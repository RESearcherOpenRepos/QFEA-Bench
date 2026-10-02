#!/usr/bin/env python3
"""Run OpenHands on QuanBench local JSONL instances."""

from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import inspect
import json
import os
import re
import shlex
import sys
import textwrap
import threading
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined


ROOT = Path(__file__).resolve().parents[4]
OPENHANDS_BENCHMARKS = ROOT / "external" / "OpenHands-benchmarks"
DEFAULT_INSTANCES = (
    ROOT
    / "benchmark"
    / "evaluation"
    / "openhands"
    / "data"
    / "instances"
    / "openhands.secure.jsonl"
)
DEFAULT_OUTPUT_DIR = ROOT / "benchmark" / "evaluation" / "openhands" / "runs"
DEFAULT_PROMPT = ROOT / "benchmark" / "evaluation" / "openhands" / "config" / "new_feature.j2"
DEFAULT_MODEL_CONFIG = (
    ROOT / "benchmark" / "evaluation" / "openhands" / "config" / "deepseek_v4_flash_official.json"
)
DEFAULT_NO_FINISH_MAX_ATTEMPTS = 2
SKIP_CACHE_REPO_UPDATE_ENV = "OPENHANDS_SKIP_CACHE_REPO_UPDATE"
SOURCE_PATCH_PATHSPEC = (
    ". ':(exclude)workspace/**' "
    "':(exclude)conversations/**' "
    "':(exclude)bash_events/**'"
)

os.environ.setdefault(SKIP_CACHE_REPO_UPDATE_ENV, "1")

sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(OPENHANDS_BENCHMARKS))


@contextlib.contextmanager
def temporary_cwd(path: Path):
    previous_cwd = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous_cwd)


from benchmark.evaluation.common.network_isolation import (  # noqa: E402
    NET_ADMIN_DOCKER_ARGS,
    build_egress_firewall_command,
)

with temporary_cwd(OPENHANDS_BENCHMARKS):
    from benchmarks.utils.acp import (  # noqa: E402
        add_acp_agent_metadata,
        build_acp_agent,
        get_acp_forward_env,
        is_acp_agent,
        setup_acp_workspace,
        workspace_keepalive,
    )
    from benchmarks.utils.agent_context import create_agent_context  # noqa: E402
    from benchmarks.utils.args_parser import get_parser  # noqa: E402
    from benchmarks.utils.console_logging import summarize_instance  # noqa: E402
    from benchmarks.utils.conversation import build_event_persistence_callback  # noqa: E402
    from benchmarks.utils.critics import create_critic  # noqa: E402
    from benchmarks.utils.dataset import get_dataset  # noqa: E402
    import benchmarks.utils.evaluation as openhands_evaluation_module  # noqa: E402
    from benchmarks.utils.evaluation import Evaluation  # noqa: E402
    from benchmarks.utils.litellm_proxy import build_eval_llm  # noqa: E402
    from benchmarks.utils.models import EvalInstance, EvalMetadata, EvalOutput  # noqa: E402
    from openhands.sdk import Agent, Conversation, LLM, Tool, get_logger  # noqa: E402
    from openhands.sdk.agent import ACPAgent  # noqa: E402
    from openhands.sdk.context.condenser import LLMSummarizingCondenser  # noqa: E402
    import openhands.sdk.git.cached_repo as openhands_cached_repo  # noqa: E402
    from openhands.sdk.llm.utils import model_features as openhands_model_features  # noqa: E402
    from openhands.sdk.workspace import RemoteWorkspace  # noqa: E402
    from openhands.tools.delegate import DelegateTool  # noqa: E402
    from openhands.workspace import DockerWorkspace  # noqa: E402
from benchmark.evaluation.common.io_utils import parse_slice_spec  # noqa: E402
from benchmark.evaluation.common.model_names import (  # noqa: E402
    prediction_model_name as artifact_model_name,
)
from benchmark.evaluation.common.run_io import write_batch_prediction_files  # noqa: E402
from benchmark.evaluation.common.task_format import (  # noqa: E402
    format_interface_contract,
    format_requirements,
)
from benchmark.evaluation.openhands.scripts.run_policy import (  # noqa: E402
    has_completion_signal,
    step_budget_exhausted,
)

from benchmark.evaluation.openhands.scripts.convert_openhands_preds import (  # noqa: E402
    convert_rows,
    estimated_row_cost,
    read_output_rows,
    sanitize_reasoning_artifacts,
    write_incremental_outputs,
    write_openhands_trajectories,
)


logger = get_logger(__name__)
PRED_LOCK = threading.Lock()
DEEPSEEK_REASONING_CONTENT_MODEL_PATTERNS = ("deepseek-v4-flash",)
ENV_VAR_PATTERN = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


class NoFinishToolError(RuntimeError):
    """Raised when OpenHands reports finished without a native completion signal."""


def patch_deepseek_reasoning_content_passthrough(model_name: str) -> None:
    """Preserve DeepSeek reasoning_content when the provider requires it.

    Some DeepSeek-compatible endpoints reject follow-up chat requests unless
    prior assistant reasoning_content is passed back. OpenHands already has
    provider support for this behavior; QuanBench only adds the model alias used
    by the benchmark without modifying the external SDK checkout.
    """
    normalized = (model_name or "").lower()
    if not any(pattern in normalized for pattern in DEEPSEEK_REASONING_CONTENT_MODEL_PATTERNS):
        return
    for pattern in DEEPSEEK_REASONING_CONTENT_MODEL_PATTERNS:
        if pattern not in openhands_model_features.SEND_REASONING_CONTENT_MODELS:
            openhands_model_features.SEND_REASONING_CONTENT_MODELS.append(pattern)


def construct_quanbench_output_dir(output_dir: str) -> str:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)


class StepProgressTracker:
    """Track and print unique OpenHands LLM-response steps."""

    def __init__(self, instance_id: str, max_iterations: int, consecutive_command_limit: int) -> None:
        self.instance_id = instance_id
        self.max_iterations = max_iterations
        self.consecutive_command_limit = max(0, consecutive_command_limit)
        self.seen_response_ids: set[str] = set()
        self.step = 0
        self.last_command = ""
        self.consecutive_count = 0
        self.repeated_command = ""
        self.exhausted_reported = False

    @property
    def exhausted(self) -> bool:
        return self.step >= self.max_iterations

    def __call__(self, event: Any) -> None:
        if event.__class__.__name__ != "ActionEvent":
            return
        tool_name = getattr(event, "tool_name", None)
        if not tool_name:
            return
        response_id = getattr(event, "llm_response_id", None)
        if response_id:
            response_id = str(response_id)
            if response_id in self.seen_response_ids:
                return
            self.seen_response_ids.add(response_id)
        command = self.action_command(event)
        if command:
            if command == self.last_command:
                self.consecutive_count += 1
            else:
                self.last_command = command
                self.consecutive_count = 1
            if self.consecutive_command_limit > 0 and self.consecutive_count >= self.consecutive_command_limit:
                self.repeated_command = command
                raise RepeatedCommandLoopError(command, self.consecutive_count, self.consecutive_command_limit)
        else:
            self.last_command = ""
            self.consecutive_count = 0
        self.step += 1
        self.print_progress(tool_name)

    def print_progress(self, tool_name: str, status: str | None = None) -> None:
        if sys.__stdout__ is not None:
            suffix = f" status={status}" if status else ""
            print(
                f"OPENHANDS_PROGRESS instance={self.instance_id} "
                f"step={self.step}/{self.max_iterations} tool={tool_name}{suffix}",
                file=sys.__stdout__,
                flush=True,
            )

    def mark_exhausted(self) -> None:
        if self.exhausted_reported:
            return
        self.exhausted_reported = True
        if self.step < self.max_iterations:
            self.step = self.max_iterations
        self.print_progress("max_iterations", status="step_exhausted")

    @staticmethod
    def action_command(event: Any) -> str:
        for name in ("command", "cmd", "input", "code"):
            value = getattr(event, name, None)
            if isinstance(value, str) and value.strip():
                return re.sub(r"\s+", " ", value).strip()
        action = getattr(event, "action", None)
        if action is not None:
            for name in ("command", "cmd", "input", "code"):
                value = getattr(action, name, None)
                if isinstance(value, str) and value.strip():
                    return re.sub(r"\s+", " ", value).strip()
        return ""


class RepeatedCommandLoopError(RuntimeError):
    """Raised when the same OpenHands command is emitted too many times in a row."""

    def __init__(self, command: str, count: int, limit: int) -> None:
        super().__init__(f"Repeated command loop detected after {count} consecutive calls: {command}")
        self.command = command
        self.count = count
        self.limit = limit


def build_step_progress_callback(
    instance_id: str,
    max_iterations: int,
    consecutive_command_limit: int,
) -> StepProgressTracker:
    """Print lightweight per-step progress lines to the instance output log."""
    return StepProgressTracker(instance_id, max_iterations, consecutive_command_limit)


def refresh_conversation(conversation: Conversation) -> None:
    with contextlib.suppress(Exception):
        conversation.state.refresh_from_server()
    with contextlib.suppress(Exception):
        conversation.state.events.reconcile()


def run_conversation_once(conversation: Conversation) -> None:
    """Run exactly one OpenHands server turn.

    The SDK iteration limit is per conversation.run() call, so QuanBench must not
    use the fake-user helper that can call run() repeatedly for one sample.
    """
    conversation.run(timeout=int(os.getenv("CONVERSATION_TIMEOUT", "3600")))


def expand_env_vars(value: Any) -> Any:
    if isinstance(value, str):
        for name in referenced_env_vars(value):
            ensure_env_var(name)
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [expand_env_vars(item) for item in value]
    if isinstance(value, dict):
        return {key: expand_env_vars(item) for key, item in value.items()}
    return value


def referenced_env_vars(value: Any) -> set[str]:
    if isinstance(value, str):
        return {match.group(1) or match.group(2) for match in ENV_VAR_PATTERN.finditer(value)}
    if isinstance(value, list):
        names: set[str] = set()
        for item in value:
            names.update(referenced_env_vars(item))
        return names
    if isinstance(value, dict):
        names: set[str] = set()
        for item in value.values():
            names.update(referenced_env_vars(item))
        return names
    return set()


def read_zshrc_export(name: str) -> str | None:
    zshrc = Path.home() / ".zshrc"
    if not zshrc.exists():
        return None
    prefix = f"{name}="
    export_prefix = f"export {name}="
    for line in zshrc.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if stripped.startswith(export_prefix):
            value = stripped[len(export_prefix) :]
        elif stripped.startswith(prefix):
            value = stripped[len(prefix) :]
        else:
            continue
        try:
            values = shlex.split(value, comments=True)
        except ValueError:
            return value.split("#", 1)[0].strip().strip("\"'")
        return values[0] if values else ""
    return None


def ensure_env_var(name: str) -> None:
    if os.getenv(name):
        return
    if value := read_zshrc_export(name):
        os.environ[name] = value


def configure_model_env(model_name: str) -> None:
    if model_name.startswith("openai/deepseek") and not os.getenv("DEEPSEEK_API_KEY"):
        ensure_env_var("DEEPSEEK_API_KEY")


def print_model_env_diagnostic(model_name: str, api_key: str = "", source: str = "api_key") -> None:
    key = api_key or ""
    fingerprint = hashlib.sha256(key.encode()).hexdigest()[:8] if key else "none"
    last4 = key[-4:] if key else "none"
    print(
        f"Model config: {model_name}; {source} visible={bool(key)} "
        f"len={len(key)} last4={last4} fingerprint={fingerprint}",
        flush=True,
    )


def normalize_instance_value(value: Any) -> Any:
    if hasattr(value, "tolist"):
        return normalize_instance_value(value.tolist())
    if isinstance(value, list):
        return [normalize_instance_value(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_instance_value(item) for key, item in value.items()}
    return value


def load_config_payload(config_path: str | Path) -> dict[str, Any]:
    return json.loads(Path(config_path).read_text(encoding="utf-8"))


def load_run_defaults(config_path: str | Path) -> dict[str, Any]:
    config = load_config_payload(config_path)
    run_config = config.get("run", {})
    if not isinstance(run_config, dict):
        raise ValueError("OpenHands config field 'run' must be an object when provided")

    defaults: dict[str, Any] = {}
    if "max_iterations" in run_config:
        defaults["max_iterations"] = int(run_config["max_iterations"])
    if "max_retries" in run_config:
        defaults["max_retries"] = int(run_config["max_retries"])
    if "no_finish_max_attempts" in run_config:
        defaults["no_finish_max_attempts"] = int(run_config["no_finish_max_attempts"])
    return defaults


def load_tool_config(config_path: str | Path) -> dict[str, Any]:
    config = load_config_payload(config_path)
    tool_config = config.get("tools", {})
    if not isinstance(tool_config, dict):
        raise ValueError("OpenHands config field 'tools' must be an object when provided")
    return tool_config


def load_agent_config(config_path: str | Path) -> dict[str, Any]:
    config = load_config_payload(config_path)
    agent_config = config.get("agent", {})
    if not isinstance(agent_config, dict):
        raise ValueError("OpenHands config field 'agent' must be an object when provided")
    if "tool_concurrency_limit" in agent_config:
        limit = int(agent_config["tool_concurrency_limit"])
        if limit < 1:
            raise ValueError("agent.tool_concurrency_limit must be positive")
        agent_config["tool_concurrency_limit"] = limit
    return agent_config


def load_prediction_model_name(config_path: str | Path, fallback: str) -> str:
    config = load_config_payload(config_path)
    return artifact_model_name(config.get("prediction_model_name") or fallback)


def load_llm_config(config_path: str | Path) -> LLM:
    config = load_config_payload(config_path)
    config.pop("run", None)
    config.pop("tools", None)
    config.pop("agent", None)
    config.pop("prediction_model_name", None)
    model_name = str(config.get("model") or "")
    configure_model_env(model_name)
    for name in sorted(referenced_env_vars(config)):
        ensure_env_var(name)
    api_key_source = ",".join(sorted(referenced_env_vars(config.get("api_key")))) or "api_key"
    config = expand_env_vars(config)
    api_key = config.get("api_key")
    if isinstance(api_key, str) and api_key.startswith("$"):
        raise ValueError(
            f"LLM config references unresolved environment variable {api_key!r}"
        )
    llm = LLM.model_validate(config)
    print_model_env_diagnostic(llm.model, str(api_key or ""), api_key_source)
    return llm


def model_endpoint_hosts(llm: LLM) -> list[str]:
    hosts: list[str] = []
    base_url = getattr(llm, "base_url", None)
    if base_url:
        parsed = urlparse(str(base_url))
        if parsed.hostname:
            hosts.append(parsed.hostname)
    if llm.model.startswith("openrouter/"):
        hosts.append("openrouter.ai")
    if llm.model.startswith("gemini/"):
        if not any(host.endswith("aiplatform.googleapis.com") for host in hosts):
            hosts.append("generativelanguage.googleapis.com")
    if llm.model.startswith("vertex_ai/"):
        hosts.extend(["aiplatform.googleapis.com", "oauth2.googleapis.com", "www.googleapis.com"])
    return sorted(set(hosts))


def patch_local_websocket_proxy() -> None:
    from openhands.sdk.conversation.impl import remote_conversation

    original_connect = remote_conversation.websockets.connect

    def connect_local_direct(uri: str, *args: Any, **kwargs: Any) -> Any:
        if (
            uri.startswith("ws://127.0.0.1:")
            or uri.startswith("ws://localhost:")
            or uri.startswith("ws://0.0.0.0:")
        ) and "proxy" not in kwargs:
            kwargs["proxy"] = None
        return original_connect(uri, *args, **kwargs)

    remote_conversation.websockets.connect = connect_local_direct


def configure_local_proxy_bypass() -> None:
    local_hosts = ["127.0.0.1", "localhost", "0.0.0.0"]
    for key in ("NO_PROXY", "no_proxy"):
        existing = os.getenv(key, "")
        entries = [entry.strip() for entry in existing.split(",") if entry.strip()]
        for host in local_hosts:
            if host not in entries:
                entries.append(host)
        os.environ[key] = ",".join(entries)


def skip_cache_repo_update_enabled() -> bool:
    value = os.getenv(SKIP_CACHE_REPO_UPDATE_ENV, "")
    return value.lower() in {"1", "true", "yes", "on"}


def patch_cached_repo_update_skip() -> None:
    """Patch SDK cached repo updates at runtime without editing SDK source."""
    original = openhands_cached_repo._do_clone_or_update
    if getattr(original, "_quanbench_skip_cache_repo_update", False):
        return

    def do_clone_or_update_with_skip(
        url: str,
        repo_path: Path,
        ref: str | None,
        update: bool,
        git: Any,
    ) -> Path:
        if (
            update
            and skip_cache_repo_update_enabled()
            and repo_path.exists()
            and (repo_path / ".git").exists()
        ):
            openhands_cached_repo.logger.debug(
                f"Skipping repository update for {repo_path} because "
                f"{SKIP_CACHE_REPO_UPDATE_ENV}=1"
            )
            update = False
        return original(url, repo_path, ref, update, git)

    do_clone_or_update_with_skip._quanbench_skip_cache_repo_update = True
    do_clone_or_update_with_skip._quanbench_original = original
    openhands_cached_repo._do_clone_or_update = do_clone_or_update_with_skip


def patch_terminal_action_timeout(timeout_seconds: float | None) -> None:
    if timeout_seconds is None:
        return
    if timeout_seconds <= 0:
        raise ValueError("tools.terminal.timeout_seconds must be positive")

    from openhands.tools.terminal.impl import TerminalExecutor

    if not hasattr(TerminalExecutor, "_quanbench_original_call"):
        TerminalExecutor._quanbench_original_call = TerminalExecutor.__call__

    original_call = TerminalExecutor._quanbench_original_call

    def call_with_configured_timeout(
        self: Any, action: Any, conversation: Any = None
    ) -> Any:
        if not getattr(action, "is_input", False):
            timeout = getattr(action, "timeout", None)
            if timeout is None or timeout > timeout_seconds:
                action = action.model_copy(update={"timeout": timeout_seconds})
        return original_call(self, action, conversation)

    TerminalExecutor.__call__ = call_with_configured_timeout
    TerminalExecutor._quanbench_timeout_seconds = timeout_seconds


def configure_tool_timeouts(tool_config: dict[str, Any]) -> None:
    terminal_config = tool_config.get("terminal", {})
    if terminal_config is None:
        terminal_config = {}
    if not isinstance(terminal_config, dict):
        raise ValueError("OpenHands config field 'tools.terminal' must be an object")
    timeout_seconds = terminal_config.get("timeout_seconds")
    if timeout_seconds is not None:
        patch_terminal_action_timeout(float(timeout_seconds))


def patch_docker_workspace_net_admin() -> None:
    """Add NET_ADMIN to OpenHands workspace containers for iptables isolation."""
    from openhands.workspace.docker import workspace as docker_workspace_module

    if hasattr(docker_workspace_module, "_quanbench_original_execute_command"):
        return

    original_execute_command = docker_workspace_module.execute_command
    docker_workspace_module._quanbench_original_execute_command = original_execute_command

    def execute_command_with_net_admin(command: Any, *args: Any, **kwargs: Any) -> Any:
        if (
            isinstance(command, list)
            and len(command) >= 3
            and command[0:3] == ["docker", "run", "-d"]
            and not any(arg.startswith("--cap-add") for arg in command)
        ):
            command = [*command[:3], *NET_ADMIN_DOCKER_ARGS, *command[3:]]
        return original_execute_command(command, *args, **kwargs)

    docker_workspace_module.execute_command = execute_command_with_net_admin


def get_tools_for_preset(preset: str) -> list[Tool]:
    if preset == "gemini":
        from openhands.tools.preset.gemini import get_gemini_tools

        return get_gemini_tools(enable_browser=False)
    if preset == "gpt5":
        from openhands.tools.preset.gpt5 import get_gpt5_tools

        return get_gpt5_tools(enable_browser=False)
    if preset == "planning":
        from openhands.tools.preset.planning import get_planning_tools

        return get_planning_tools()
    from openhands.tools.preset.default import get_default_tools

    return get_default_tools(enable_browser=False)


def render_instruction(instance: dict[str, Any], metadata: EvalMetadata, workspace_path: str) -> str:
    assert metadata.prompt_path is not None
    prompt_path = Path(metadata.prompt_path)
    env = Environment(
        loader=FileSystemLoader(str(prompt_path.parent)),
        undefined=StrictUndefined,
    )
    template = env.get_template(prompt_path.name)
    return template.render(
        instance=instance,
        workspace_dir_name=instance["repo"].split("/")[-1],
        actual_workspace_path=workspace_path,
        metadata=metadata,
        repo_path=instance["repo_path"],
        feature_goal=instance["problem_statement"],
        acceptance_requirements=format_requirements(instance.get("requirements") or []),
        public_interface_contract=format_interface_contract(instance.get("interface") or []),
    )


def prepare_quanbench_dataframe(metadata: EvalMetadata) -> Any:
    """Load QuanBench instances while preserving JSONL order for --n-limit/--slice.

    OpenHands-benchmarks applies ``DataFrame.sample(..., random_state=42)`` when
    ``eval_limit`` is set. QuanBench uses ordered selection so results can be
    compared directly with the mini-SWE-agent and Trae-agent runners.
    """
    df = get_dataset(
        dataset_name=metadata.dataset,
        split=metadata.dataset_split,
        eval_limit=None,
        selected_instances_file=metadata.selected_instances_file,
    )
    details = getattr(metadata, "details", None) or {}
    selection = details.get("selection") if isinstance(details, dict) else None
    slice_spec = None
    if isinstance(selection, dict):
        slice_spec = selection.get("slice")
    if slice_spec is None:
        slice_spec = getattr(metadata, "quanbench_slice", None)
    parsed_slice = parse_slice_spec(slice_spec)
    if parsed_slice is not None:
        df = df.iloc[parsed_slice]
    if metadata.eval_limit is not None and metadata.eval_limit > 0:
        df = df.head(metadata.eval_limit)
    return df


def prune_resume_file(path: Path, selected_ids: set[str], critic: Any) -> None:
    """Keep only successful rows for the current selected instance set."""
    del critic
    if not path.exists():
        return

    kept: list[str] = []
    changed = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            output = EvalOutput.model_validate(json.loads(line))
            manual_failed = bool(
                output.test_result and output.test_result.get("manual_failed")
            )
            step_budget_exhausted = bool(
                output.test_result and output.test_result.get("step_budget_exhausted")
            )
            git_patch = (
                output.test_result.get("git_patch", "")
                if isinstance(output.test_result, dict)
                else ""
            )
            is_complete = (
                output.instance_id in selected_ids
                and not manual_failed
                and (
                    step_budget_exhausted
                    or (
                        not output.error
                        and bool(git_patch.strip())
                        and has_completion_signal(list(output.history or []))
                    )
                )
            )
        except Exception:
            is_complete = False
        if is_complete:
            kept.append(line)
        else:
            changed = True

    if changed:
        path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")


def prune_resume_state(metadata: EvalMetadata, critic: Any) -> None:
    """Remove stale failed/out-of-scope rows that would otherwise be skipped."""
    output_dir = Path(metadata.eval_output_dir)
    df = prepare_quanbench_dataframe(metadata)
    selected_ids = {str(row["instance_id"]) for _, row in df.iterrows()}
    paths = [output_dir / "output.jsonl"]
    paths.extend(sorted(output_dir.glob("output.critic_attempt_*.jsonl")))
    for path in paths:
        prune_resume_file(path, selected_ids, critic)


def normalize_eval_output_cost(out: EvalOutput, model_name: str) -> EvalOutput:
    """Patch OpenHands' raw cost fields when provider cost accounting is partial."""
    row = json.loads(out.model_dump_json())
    metrics = row.get("metrics")
    if not isinstance(metrics, dict):
        return out

    estimated_cost = estimated_row_cost(row, model_name)
    if estimated_cost is None:
        return out

    metrics["accumulated_cost"] = estimated_cost
    costs = metrics.get("costs")
    if not isinstance(costs, list):
        costs = []

    cost_sum = 0.0
    for item in costs:
        if not isinstance(item, dict):
            continue
        try:
            cost_sum += float(item.get("cost") or 0.0)
        except (TypeError, ValueError):
            continue

    if abs(cost_sum - estimated_cost) > 1e-12:
        if cost_sum <= estimated_cost:
            costs.append({"model": model_name, "cost": estimated_cost - cost_sum})
        else:
            costs = [{"model": model_name, "cost": estimated_cost}]
        metrics["costs"] = costs

    return EvalOutput.model_validate(row)


def patch_evaluation_retry_limit_hook() -> None:
    """Patch OpenHands Evaluation in memory to honor per-exception retry caps."""
    if getattr(
        Evaluation._execute_single_attempt,
        "_quanbench_retry_limit_hook",
        False,
    ):
        return

    source = textwrap.dedent(inspect.getsource(Evaluation._execute_single_attempt))
    failure_block = (
        "        failure_category = classify_failure(e)\n"
        "        escalate = failure_category == FailureCategory.RESOURCE\n"
    )
    if failure_block not in source:
        raise RuntimeError(
            "OpenHands Evaluation retry block changed; update QuanBench patch"
        )
    source = source.replace(
        "        conversation_archive_path: Path | None = None\n",
        "        conversation_archive_path: Path | None = None\n"
        "        effective_max_retries = max_retries\n",
        1,
    )
    source = source.replace(
        failure_block,
        "        failure_category = classify_failure(e)\n"
        "        escalate = failure_category == FailureCategory.RESOURCE\n"
        "        retry_limit_hook = getattr(self, '_max_retries_for_exception', None)\n"
        "        effective_max_retries = (\n"
        "            retry_limit_hook(e, max_retries)\n"
        "            if retry_limit_hook is not None\n"
        "            else max_retries\n"
        "        )\n",
    )
    source = source.replace(
        "retry_count < max_retries",
        "retry_count < effective_max_retries",
    )
    source = source.replace(
        "attempt {retry_count + 1}/{max_retries + 1}",
        "attempt {retry_count + 1}/{effective_max_retries + 1}",
    )
    source = source.replace(
        "failed after \"\n                    f\"{max_retries + 1} attempts",
        "failed after \"\n                    f\"{effective_max_retries + 1} attempts",
    )
    source = source.replace(
        "                    max_retries,\n                    metrics=recovered_metrics,",
        "                    effective_max_retries,\n                    metrics=recovered_metrics,",
    )

    namespace: dict[str, Any] = {}
    exec(source, openhands_evaluation_module.__dict__, namespace)
    patched = namespace["_execute_single_attempt"]
    patched._quanbench_retry_limit_hook = True
    Evaluation._execute_single_attempt = patched


def write_sanitized_eval_output(output_path: str, row: dict[str, Any]) -> None:
    row = sanitize_reasoning_artifacts(row)
    target_path = (
        output_path.replace(".jsonl", "_errors.jsonl")
        if row.get("error")
        else output_path
    )
    with open(target_path, "a", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        fcntl.flock(handle, fcntl.LOCK_UN)


def build_quanbench_on_result_writer(output_path: str, model_name: str):
    output_dir = Path(output_path).parent

    def _cb(instance: EvalInstance, out: EvalOutput) -> None:
        del instance
        out = normalize_eval_output_cost(out, model_name)
        row = json.loads(out.model_dump_json())
        row = sanitize_reasoning_artifacts(row)
        write_sanitized_eval_output(output_path, row)
        write_incremental_outputs(output_dir, row, model_name, lock=PRED_LOCK)

    return _cb


class QuanBenchOpenHandsEvaluation(Evaluation):
    """OpenHands evaluation for prebuilt QuanBench agent-server images."""

    def _max_retries_for_exception(self, error: Exception, max_retries: int) -> int:
        if not isinstance(error, NoFinishToolError):
            return max_retries

        details = self.metadata.details or {}
        run_details = details.get("run") if isinstance(details, dict) else {}
        configured = (
            run_details.get("no_finish_max_attempts")
            if isinstance(run_details, dict)
            else None
        )
        try:
            max_attempts = int(
                configured
                if configured is not None
                else DEFAULT_NO_FINISH_MAX_ATTEMPTS
            )
        except (TypeError, ValueError):
            max_attempts = DEFAULT_NO_FINISH_MAX_ATTEMPTS

        return min(max_retries, max(1, max_attempts) - 1)

    def prepare_instances(self) -> list[EvalInstance]:
        df = prepare_quanbench_dataframe(self.metadata)
        instances = []
        for _, row in df.iterrows():
            data = normalize_instance_value(row.to_dict())
            instances.append(EvalInstance(id=str(data["instance_id"]), data=data))
        logger.info("Total instances to process: %d", len(instances))
        return instances

    def prepare_workspace(
        self,
        instance: EvalInstance,
        resource_factor: int = 1,
        forward_env: list[str] | None = None,
    ) -> RemoteWorkspace:
        del resource_factor
        forward_env = get_acp_forward_env(self.metadata.agent_type, forward_env)
        image_name = str(instance.data["image_name"])
        workspace = DockerWorkspace(
            server_image=image_name,
            platform=str(instance.data.get("platform") or "linux/amd64"),
            working_dir="/workspace",
            forward_env=forward_env or [],
        )
        for cmd in self.metadata.env_setup_commands or []:
            res = workspace.execute_command(cmd)
            if res.exit_code != 0:
                raise RuntimeError(
                    f"Failed to run env setup command {cmd!r}: {res.stderr}"
                )
        return workspace

    def evaluate_instance(
        self,
        instance: EvalInstance,
        workspace: RemoteWorkspace,
    ) -> EvalOutput:
        if is_acp_agent(self.metadata.agent_type):
            agent = build_acp_agent(self.metadata.agent_type, self.metadata.llm.model)
        else:
            agent_llm = build_eval_llm(self.metadata.llm)
            tools = get_tools_for_preset(self.metadata.tool_preset)
            if self.metadata.enable_delegation:
                tools.append(Tool(name=DelegateTool.name))
            condenser = None
            if self.metadata.enable_condenser:
                condenser = LLMSummarizingCondenser(
                    llm=build_eval_llm(self.metadata.llm, usage_id="condenser"),
                    max_size=self.metadata.condenser_max_size,
                    keep_first=self.metadata.condenser_keep_first,
                )
            agent = Agent(
                llm=agent_llm,
                tools=tools,
                system_prompt_kwargs={"cli_mode": True},
                condenser=condenser,
                agent_context=create_agent_context(),
                **((self.metadata.details or {}).get("agent", {})),
            )

        assert isinstance(workspace, RemoteWorkspace)
        setup_acp_workspace(self.metadata.agent_type, workspace)

        repo_path = "/workspace/repo"
        source_repo_path = str(instance.data.get("source_repo_path") or "/workspace/repo")
        instance.data["repo_path"] = repo_path
        instance.data["max_iterations"] = self.metadata.max_iterations

        persist_callback = build_event_persistence_callback(
            run_id=self.metadata.eval_output_dir,
            instance_id=instance.id,
            attempt=self.current_attempt,
        )
        progress_callback = build_step_progress_callback(
            instance_id=instance.id,
            max_iterations=self.metadata.max_iterations,
            consecutive_command_limit=int(
                ((self.metadata.details or {}).get("repeated_command") or {}).get(
                    "consecutive_command_limit",
                    6,
                )
            ),
        )
        conversation = Conversation(
            agent=agent,
            workspace=workspace,
            callbacks=[progress_callback, persist_callback],
            max_iteration_per_run=self.metadata.max_iterations,
            stuck_detection=False,
            delete_on_close=True,
        )

        try:
            prepare_repo = workspace.execute_command(
                f"test -d {repo_path}/.git || "
                f"(mkdir -p {repo_path} && cp -r {source_repo_path}/. {repo_path})"
            )
            assert prepare_repo.exit_code == 0, f"prepare repo failed: {prepare_repo.stderr}"

            base_commit = str(instance.data["base_commit"])
            reset_repo = workspace.execute_command(
                f"cd {repo_path} ; git reset --hard {base_commit} ; git clean -fdx"
            )
            assert reset_repo.exit_code == 0, f"git reset failed: {reset_repo.stderr}"

            instruction = render_instruction(instance.data, self.metadata, workspace.working_dir)

            def empty_output(
                *,
                exhausted: bool,
                repeated_command_loop: bool = False,
                repeated_command: str = "",
                consecutive_count: int | None = None,
                consecutive_command_limit: int | None = None,
            ) -> EvalOutput:
                return EvalOutput(
                    instance_id=instance.id,
                    attempt=self.current_attempt,
                    test_result={
                        "git_patch": "",
                        "step_budget_exhausted": exhausted,
                        "repeated_command_loop": repeated_command_loop,
                        "repeated_command": repeated_command,
                        "consecutive_count": consecutive_count,
                        "consecutive_command_limit": consecutive_command_limit,
                    },
                    instruction=instruction,
                    error=None,
                    history=list(conversation.state.events),
                    metrics=conversation.conversation_stats.get_combined_metrics(),
                    instance=instance.data,
                )

            with workspace_keepalive(self.metadata.agent_type, workspace):
                conversation.send_message(instruction)

                def run_checked() -> tuple[list[Any], EvalOutput | None]:
                    try:
                        run_conversation_once(conversation)
                    except RepeatedCommandLoopError as exc:
                        refresh_conversation(conversation)
                        return (
                            list(conversation.state.events),
                            empty_output(
                                exhausted=False,
                                repeated_command_loop=True,
                                repeated_command=exc.command,
                                consecutive_count=exc.count,
                                consecutive_command_limit=exc.limit,
                            ),
                        )
                    except Exception:
                        refresh_conversation(conversation)
                        events = list(conversation.state.events)
                        if not step_budget_exhausted(
                            events=events,
                            max_iterations=self.metadata.max_iterations,
                            observed_steps=progress_callback.step,
                        ):
                            raise
                        progress_callback.mark_exhausted()
                        return events, empty_output(exhausted=True)

                    refresh_conversation(conversation)
                    events = list(conversation.state.events)
                    if step_budget_exhausted(
                        events=events,
                        max_iterations=self.metadata.max_iterations,
                        observed_steps=progress_callback.step,
                    ):
                        progress_callback.mark_exhausted()
                        return events, empty_output(exhausted=True)
                    return events, None

                events, early_output = run_checked()
                if early_output is not None:
                    return early_output
                if not has_completion_signal(events):
                    raise NoFinishToolError(
                        "OpenHands finished without a native completion signal; "
                        "treating as retryable failure."
                    )

            workspace.execute_command(
                f"cd {repo_path} ; git add -A -- {SOURCE_PATCH_PATHSPEC}"
            )
            workspace.execute_command(
                f"cd {repo_path} && "
                "git config --global user.email 'openhands@all-hands.dev' && "
                "git config --global user.name 'OpenHands' && "
                "git commit --no-verify -m 'openhands changes'"
            )
            diff = workspace.execute_command(
                f"cd {repo_path} ; git --no-pager diff --no-color "
                f"{base_commit} HEAD -- {SOURCE_PATCH_PATHSPEC}"
            )
            assert diff.exit_code == 0, f"git diff failed: {diff.stderr}"
            git_patch = diff.stdout

            summarize_instance(
                instance_id=instance.id,
                conversation=conversation,
                git_patch=git_patch,
                logger=logger,
            )

            test_result: dict[str, Any] = {"git_patch": git_patch}
            if isinstance(agent, ACPAgent):
                add_acp_agent_metadata(test_result, conversation)

            output = EvalOutput(
                instance_id=instance.id,
                attempt=self.current_attempt,
                test_result=test_result,
                instruction=instruction,
                error=None,
                history=list(conversation.state.events),
                metrics=conversation.conversation_stats.get_combined_metrics(),
                instance=instance.data,
            )
        finally:
            conversation.close()

        return output


def add_prompt_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--prompt-config",
        dest="prompt_path",
        type=Path,
        default=DEFAULT_PROMPT,
        help="Jinja prompt template for OpenHands.",
    )
    parser.add_argument(
        "--prompt-path",
        dest="prompt_path",
        type=Path,
        help=argparse.SUPPRESS,
    )


def add_selection_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--slice", default=None, help="Python slice syntax, e.g. 0:5.")
    parser.add_argument(
        "--consecutive-command-limit",
        type=int,
        default=6,
        help="Fail an instance after the same tool command is emitted this many times consecutively. Use 0 to disable.",
    )
    parser.add_argument(
        "--no-finish-max-attempts",
        type=int,
        default=DEFAULT_NO_FINISH_MAX_ATTEMPTS,
        help=(
            "Maximum total attempts for OpenHands runs that finish without a "
            "native completion signal, i.e. neither finish tool nor final "
            "agent message. The default is 2 total attempts, i.e. retry once. "
            "Other exception retries still use --max-retries."
        ),
    )


def add_model_config_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "llm_config_path",
        nargs="?",
        default=None,
        help="Backward-compatible positional model config path.",
    )
    parser.add_argument(
        "--model-config",
        dest="model_config_path",
        type=Path,
        default=None,
        help="OpenHands LLM/model config JSON.",
    )


def main() -> None:
    if not OPENHANDS_BENCHMARKS.exists():
        raise FileNotFoundError(f"OpenHands benchmarks repo not found: {OPENHANDS_BENCHMARKS}")

    parser = get_parser(add_llm_config=False)
    add_model_config_argument(parser)
    add_prompt_argument(parser)
    add_selection_arguments(parser)
    parser.set_defaults(
        dataset=str(DEFAULT_INSTANCES),
        split="train",
        workspace="docker",
        output_dir=str(DEFAULT_OUTPUT_DIR),
        num_workers=1,
        n_critic_runs=1,
        disable_condenser=True,
        condenser_max_size=240,
        condenser_keep_first=2,
    )
    known_args = parser.parse_known_args()[0]
    model_config_path = known_args.model_config_path or known_args.llm_config_path or DEFAULT_MODEL_CONFIG
    config_defaults = load_run_defaults(model_config_path)
    parser.set_defaults(**config_defaults)
    args = parser.parse_args()
    if args.n_limit and args.n_limit > 0 and args.slice:
        raise ValueError("Use either --slice or --n-limit, not both")
    args.llm_config_path = str(args.model_config_path or args.llm_config_path or DEFAULT_MODEL_CONFIG)

    if args.workspace != "docker":
        raise ValueError("QuanBench OpenHands runner currently supports --workspace docker only")

    patch_local_websocket_proxy()
    configure_local_proxy_bypass()
    patch_cached_repo_update_skip()
    patch_docker_workspace_net_admin()
    tool_config = load_tool_config(args.llm_config_path)
    agent_config = load_agent_config(args.llm_config_path)
    configure_tool_timeouts(tool_config)
    llm = load_llm_config(args.llm_config_path)
    patch_deepseek_reasoning_content_passthrough(llm.model)
    prediction_model_name = load_prediction_model_name(args.llm_config_path, llm.model)
    print(f"Prediction model label: {prediction_model_name}", flush=True)
    structured_output_dir = construct_quanbench_output_dir(args.output_dir)

    enable_condenser = args.enable_condenser
    if args.disable_condenser:
        enable_condenser = False
    critic = create_critic(args)

    metadata = EvalMetadata(
        llm=llm,
        dataset=args.dataset,
        dataset_split=args.split,
        max_iterations=args.max_iterations,
        eval_output_dir=structured_output_dir,
        details={
            "tools": tool_config,
            "agent": agent_config,
            "run": {"no_finish_max_attempts": args.no_finish_max_attempts},
            "selection": {"slice": args.slice},
            "repeated_command": {"consecutive_command_limit": args.consecutive_command_limit},
        },
        prompt_path=str(args.prompt_path),
        eval_limit=args.n_limit,
        env_setup_commands=[
            build_egress_firewall_command(
                allowed_tcp_hosts=model_endpoint_hosts(llm),
                allow_dns=True,
            )
        ],
        n_critic_runs=args.n_critic_runs,
        critic=critic,
        selected_instances_file=args.select,
        max_retries=args.max_retries,
        workspace_type=args.workspace,
        tool_preset=args.tool_preset,
        enable_delegation=args.enable_delegation,
        agent_type=args.agent_type,
        enable_condenser=enable_condenser,
        condenser_max_size=args.condenser_max_size,
        condenser_keep_first=args.condenser_keep_first,
    )
    prune_resume_state(metadata, critic)
    patch_evaluation_retry_limit_hook()

    evaluator = QuanBenchOpenHandsEvaluation(
        metadata=metadata,
        num_workers=args.num_workers,
    )
    evaluator.run(
        on_result=build_quanbench_on_result_writer(
            evaluator.output_path,
            prediction_model_name,
        )
    )
    raw_rows = read_output_rows(Path(evaluator.output_path))
    prediction_rows = convert_rows(raw_rows, prediction_model_name)
    predictions_jsonl, predictions_json = write_batch_prediction_files(
        Path(structured_output_dir),
        prediction_rows,
    )
    write_openhands_trajectories(raw_rows, Path(structured_output_dir))
    print(
        json.dumps(
            {
                "output_json": str(evaluator.output_path),
                "preds_json": str(predictions_json),
                "preds_jsonl": str(predictions_jsonl),
            }
        )
    )


if __name__ == "__main__":
    main()
