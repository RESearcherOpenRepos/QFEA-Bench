#!/usr/bin/env python3
"""Run mini-SWE-agent on benchmark SWE-agent-style instances.

This runner intentionally stays close to mini-SWE-agent's official SWE-bench
runner while accepting this benchmark's existing JSONL instance format.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shlex
import sys
import threading
import time
import traceback
from urllib.parse import urlsplit, urlunsplit
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from jinja2 import Environment, FileSystemLoader, StrictUndefined, Template

from minisweagent.agents.default import DefaultAgent
from minisweagent.config import get_config_from_spec
from minisweagent.environments.docker import DockerEnvironment
from minisweagent.exceptions import InterruptAgentFlow
from minisweagent.models import get_model
from minisweagent.utils.log import add_file_handler, logger
from minisweagent.utils.serialize import UNSET, recursive_merge

from benchmark.evaluation.common.output_schema import (
    annotate_summary,
    default_agent_metrics,
    normalize_agent_metrics,
    trajectory_path,
    write_trajectory,
)
from benchmark.evaluation.common.io_utils import filter_by_instance_id, read_json, read_jsonl
from benchmark.evaluation.common.model_names import prediction_model_name as artifact_model_name
from benchmark.evaluation.common.run_io import write_prediction_artifacts
from benchmark.evaluation.common.task_format import (
    format_interface_contract,
    format_requirements,
)
from benchmark.evaluation.common.model_pricing import estimated_cost_usd
from benchmark.evaluation.common.redaction import redact_json_file
from benchmark.evaluation.common.token_usage import (
    token_records_from_usages,
    token_totals_from_records,
)


DEFAULT_INSTANCES = (
    ROOT
    / "benchmark"
    / "evaluation"
    / "minisweagent"
    / "data"
    / "instances"
    / "sweagent.secure.jsonl"
)
DEFAULT_OUTPUT_DIR = ROOT / "benchmark" / "evaluation" / "minisweagent" / "runs" / "debug"
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_PROMPT_CONFIG = ROOT / "benchmark" / "evaluation" / "minisweagent" / "config" / "new_feature.yaml"
DEFAULT_MODEL_CONFIG = (
    ROOT / "benchmark" / "evaluation" / "minisweagent" / "config" / "deepseek_v4_flash_official.yaml"
)
DEFAULT_CONFIGS = [DEFAULT_PROMPT_CONFIG, DEFAULT_MODEL_CONFIG]
DEFAULT_COMMON_PROMPT = (
    ROOT / "benchmark" / "evaluation" / "minisweagent" / "config" / "new_feature_common.j2"
)
DEFAULT_ENVIRONMENT_PROMPT = (
    ROOT / "benchmark" / "evaluation" / "minisweagent" / "config" / "environment.j2"
)
DEFAULT_SUBMIT_PROMPT = ROOT / "benchmark" / "evaluation" / "minisweagent" / "config" / "submit.j2"
DEFAULT_SKILL_PROMPT = ROOT / "benchmark" / "evaluation" / "minisweagent" / "config" / "skill.j2"
DEFAULT_REPRESENTATION_SKILL = ROOT / "benchmark" / "evaluation" / "rq4_representation_skill" / "SKILL.md"
SUBMIT_MARKER = "COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT"
PRED_LOCK = threading.Lock()
ENV_VAR_PATTERN = re.compile(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))")


def count_assistant_responses(traj: dict[str, Any]) -> int:
    messages = traj.get("messages")
    if not isinstance(messages, list):
        return 0
    return sum(
        1
        for message in messages
        if isinstance(message, dict) and message.get("role") == "assistant"
    )


def token_usage_by_step_from_traj(traj: dict[str, Any]) -> tuple[list[dict[str, int]], list[dict[str, int]]]:
    usages: list[dict[str, Any]] = []
    for message in traj.get("messages") or []:
        if not isinstance(message, dict) or message.get("role") != "assistant":
            continue
        response = ((message.get("extra") or {}).get("response") or {})
        usages.append(response.get("usage") or {})
    return token_records_from_usages(usages)


def model_name_from_trajectory(traj: dict[str, Any]) -> str | None:
    model_name = traj.get("model_name")
    if isinstance(model_name, str) and model_name.strip():
        return model_name
    info = traj.get("info") or {}
    config_model = (((info.get("config") or {}).get("model") or {}).get("model_name"))
    if isinstance(config_model, str) and config_model.strip():
        return config_model
    return None


def extract_trajectory_metrics(path: Path) -> dict[str, Any]:
    agent = default_agent_metrics()
    if not path.exists():
        return agent
    try:
        traj = read_json(path)
    except (OSError, json.JSONDecodeError):
        return agent
    if isinstance(traj.get("agent"), dict):
        return normalize_agent_metrics(traj["agent"])
    traj = traj.get("raw_output") or traj

    info = traj.get("info") or {}
    model_stats = info.get("model_stats") or {}
    token_by_step, cumulative_token_by_step = token_usage_by_step_from_traj(traj)
    token_totals = token_totals_from_records(token_by_step)
    instance_cost = model_stats.get("instance_cost")
    cost_metrics = {
        "input_tokens": token_totals["input_tokens"] or model_stats.get("input_tokens"),
        "cached_input_tokens": token_totals["cached_input_tokens"],
        "cache_creation_input_tokens": token_totals["cache_creation_input_tokens"],
        "output_tokens": token_totals["output_tokens"] or model_stats.get("output_tokens"),
    }
    estimated_instance_cost = estimated_cost_usd(model_name_from_trajectory(traj), cost_metrics)
    if estimated_instance_cost is not None and estimated_instance_cost > 0:
        instance_cost = round(estimated_instance_cost, 6)
    exit_status = info.get("exit_status")
    agent.update(
        {
            "steps": count_assistant_responses(traj),
            "input_tokens": model_stats.get("input_tokens") or token_totals["input_tokens"],
            "output_tokens": model_stats.get("output_tokens") or token_totals["output_tokens"],
            "instance_cost": instance_cost,
            "success": exit_status == "Submitted",
            "run_completed": is_completed_trajectory(path),
            "step_budget_exhausted": exit_status == "LimitsExceeded",
            "repeated_command_loop": exit_status == "RepeatedCommandLoop",
            "repeated_command": info.get("repeated_command"),
            "consecutive_count": info.get("consecutive_count"),
            "consecutive_command_limit": info.get("consecutive_command_limit"),
            "exit_status": exit_status,
            "cached_input_tokens": token_totals["cached_input_tokens"],
            "cache_creation_input_tokens": token_totals["cache_creation_input_tokens"],
            "token_by_step": token_by_step,
            "cumulative_token_by_step": cumulative_token_by_step,
        }
    )
    return agent


def is_completed_trajectory(path: Path) -> bool:
    """Return whether a trajectory represents a finished agent run."""
    if not path.exists():
        return False
    try:
        traj = read_json(path)
    except (OSError, json.JSONDecodeError):
        return False
    if isinstance(traj.get("raw_output"), dict):
        traj = traj["raw_output"]
    info = traj.get("info") or {}
    exit_status = info.get("exit_status")
    if exit_status == "Submitted" and bool((info.get("submission") or "").strip()):
        return True
    # mini-SWE-agent records step/cost budget exhaustion as a normal exit
    # message with an empty submission. Treat it as a completed agent run so
    # resume does not grant the instance another budget.
    return exit_status in {"LimitsExceeded", "RepeatedCommandLoop"}


def submission_from_trajectory(path: Path) -> str:
    """Return the submitted patch recorded in a completed trajectory."""
    try:
        traj = read_json(path)
    except (OSError, json.JSONDecodeError):
        return ""
    if isinstance(traj.get("raw_output"), dict):
        traj = traj["raw_output"]
    info = traj.get("info") or {}
    return str(info.get("submission") or "")


class ProgressAgent(DefaultAgent):
    """DefaultAgent that prints compact per-step progress."""

    def __init__(
        self,
        *args: Any,
        instance_id: str,
        consecutive_command_limit: int = 6,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.instance_id = instance_id
        self.consecutive_command_limit = max(0, consecutive_command_limit)
        self._last_action_command = ""
        self._consecutive_action_count = 0

    @staticmethod
    def _action_command(action: Any) -> str:
        if isinstance(action, dict):
            command = action.get("command")
            if isinstance(command, str):
                return re.sub(r"\s+", " ", command).strip()
        return ""

    def _check_repeated_action(self, action: Any) -> None:
        if self.consecutive_command_limit <= 0:
            return
        command = self._action_command(action)
        if not command:
            self._last_action_command = ""
            self._consecutive_action_count = 0
            return
        if command == self._last_action_command:
            self._consecutive_action_count += 1
        else:
            self._last_action_command = command
            self._consecutive_action_count = 1
        if self._consecutive_action_count >= self.consecutive_command_limit:
            raise InterruptAgentFlow(
                self.model.format_message(
                    role="exit",
                    content="RepeatedCommandLoop",
                    extra={
                        "exit_status": "RepeatedCommandLoop",
                        "submission": "",
                        "repeated_command": command,
                        "consecutive_count": self._consecutive_action_count,
                        "consecutive_command_limit": self.consecutive_command_limit,
                    },
                )
            )

    def step(self) -> list[dict]:
        print(f"[{self.instance_id}] step {self.n_calls + 1}", flush=True)
        return super().step()

    def execute_actions(self, message: dict) -> list[dict]:
        for action in message.get("extra", {}).get("actions", []):
            self._check_repeated_action(action)
        return super().execute_actions(message)


def render_common_task_prompt(
    *,
    repo_path: str,
    feature_goal: str,
    acceptance_requirements: str,
    public_interface_contract: str,
) -> str:
    env = Environment(
        loader=FileSystemLoader(str(DEFAULT_COMMON_PROMPT.parent)),
        undefined=StrictUndefined,
    )
    template = env.get_template(DEFAULT_COMMON_PROMPT.name)
    return template.render(
        repo_path=repo_path,
        feature_goal=feature_goal,
        acceptance_requirements=acceptance_requirements,
        public_interface_contract=public_interface_contract,
    )


def render_submit_prompt() -> str:
    return DEFAULT_SUBMIT_PROMPT.read_text(encoding="utf-8").strip()


def render_environment_prompt() -> str:
    return DEFAULT_ENVIRONMENT_PROMPT.read_text(encoding="utf-8").strip()


def load_task_fields(samples_dir: Path, instance_id: str, fallback_statement: str) -> dict[str, str]:
    sample_path = samples_dir / instance_id / "sample.json"
    if not sample_path.exists():
        matches = sorted(samples_dir.rglob(f"{instance_id}/sample.json"))
        sample_path = matches[0] if matches else sample_path
    if not sample_path.exists():
        feature_goal = fallback_statement.strip()
        acceptance_requirements = "(Structured acceptance requirements were not available.)"
        public_interface_contract = "(Structured public interface contract was not available.)"
        return {
            "feature_goal": feature_goal,
            "acceptance_requirements": acceptance_requirements,
            "public_interface_contract": public_interface_contract,
            "common_task_prompt": render_common_task_prompt(
                repo_path="/workspace/repo",
                feature_goal=feature_goal,
                acceptance_requirements=acceptance_requirements,
                public_interface_contract=public_interface_contract,
            ),
            "submit_prompt": render_submit_prompt(),
            "environment_prompt": render_environment_prompt(),
            "protected_test_paths": [],
            "sample_path": "",
        }

    sample = read_json(sample_path)
    task = sample["task"]
    feature_goal = task["problem_statement"].strip()
    acceptance_requirements = format_requirements(task.get("requirements") or [])
    public_interface_contract = format_interface_contract(
        task.get("interface") or [],
        code_spans=True,
        strip_names=True,
    )
    return {
        "feature_goal": feature_goal,
        "acceptance_requirements": acceptance_requirements,
        "public_interface_contract": public_interface_contract,
        "common_task_prompt": render_common_task_prompt(
            repo_path="/workspace/repo",
            feature_goal=feature_goal,
            acceptance_requirements=acceptance_requirements,
            public_interface_contract=public_interface_contract,
        ),
        "submit_prompt": render_submit_prompt(),
        "environment_prompt": render_environment_prompt(),
        "protected_test_paths": protected_validation_test_paths(sample),
        "sample_path": str(sample_path),
    }


def selector_file_path(selector: str) -> str:
    return selector.split("::", 1)[0].strip()


def protected_validation_test_paths(sample: dict[str, Any]) -> list[str]:
    paths: set[str] = set()
    validation = sample.get("validation") or {}
    for target in ("base", "patched"):
        target_validation = validation.get(target) or {}
        for suite in ("fail_pass", "pass_pass"):
            for selector in (target_validation.get(suite) or {}).get("file_list") or []:
                if isinstance(selector, str) and selector_file_path(selector):
                    paths.add(selector_file_path(selector))
    return sorted(paths)


def normalize_instance(row: dict[str, Any]) -> dict[str, Any]:
    if "env" in row:
        env = row["env"]
        deployment = env["deployment"]
        problem = row["problem_statement"]
        return {
            "instance_id": problem["id"],
            "problem_statement": problem["text"],
            "image_name": deployment["image"],
            "docker_args": deployment.get("docker_args", []),
            "platform": deployment.get("platform"),
            "post_startup_commands": env.get("post_startup_commands", []),
            "post_startup_command_timeout": env.get("post_startup_command_timeout", 30),
        }
    return {
        "instance_id": row["instance_id"],
        "problem_statement": row["problem_statement"],
        "image_name": row["image_name"],
        "docker_args": [],
        "platform": "linux/amd64",
        "post_startup_commands": [],
        "post_startup_command_timeout": 30,
    }


def enrich_instances_with_task_fields(instances: list[dict[str, Any]], samples_dir: Path) -> list[dict[str, Any]]:
    enriched = []
    for instance in instances:
        enriched.append(
            {
                **instance,
                **load_task_fields(samples_dir, instance["instance_id"], instance["problem_statement"]),
            }
        )
    return enriched


def parse_skill_metadata(skill_path: Path) -> dict[str, str]:
    text = skill_path.read_text(encoding="utf-8")
    metadata = {"name": skill_path.parent.name, "description": ""}
    if not text.startswith("---\n"):
        return metadata
    frontmatter, separator, _body = text[4:].partition("\n---\n")
    if not separator:
        return metadata
    for line in frontmatter.splitlines():
        key, sep, value = line.partition(":")
        if sep and key.strip() in {"name", "description"}:
            metadata[key.strip()] = value.strip().strip("'\"")
    return metadata


def representation_skill_registry_prompt(skill_path: Path, template_path: Path) -> str:
    metadata = parse_skill_metadata(skill_path)
    skill_name = metadata["name"]
    skill_description = metadata["description"]
    container_path = f"/workspace/skills/{skill_name}/SKILL.md"
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_path.name)
    return template.render(
        skills_root="/workspace/skills",
        skills=[
            {
                "name": skill_name,
                "description": skill_description,
                "path": container_path,
            }
        ],
    ).strip()


def enable_representation_skill_for_instances(
    instances: list[dict[str, Any]],
    *,
    skill_path: Path,
    skill_prompt_template: Path,
) -> list[dict[str, Any]]:
    enabled_count = 0
    enriched: list[dict[str, Any]] = []
    skill_prompt = representation_skill_registry_prompt(skill_path, skill_prompt_template)
    metadata = parse_skill_metadata(skill_path)
    for instance in instances:
        enabled_count += 1
        enriched.append(
            {
                **instance,
                "representation_skill_enabled": True,
                "representation_skill_host_dir": str(skill_path.parent),
                "representation_skill_name": metadata["name"],
                "common_task_prompt": f"{instance['common_task_prompt']}\n\n{skill_prompt}",
            }
        )
    print(
        f"Representation skill enabled for {enabled_count}/{len(instances)} selected instances.",
        flush=True,
    )
    return enriched


def load_config(config_specs: list[str | Path], model_name: str | None) -> dict[str, Any]:
    configs = [get_config_from_spec(spec) for spec in config_specs]
    configs.append({"model": {"model_name": model_name or UNSET}})
    return expand_env_vars(recursive_merge(*configs))


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


def ensure_env_var(name: str) -> None:
    if os.getenv(name):
        return
    if value := read_zshrc_export(name):
        os.environ[name] = value


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


def prepare_env_config(config: dict[str, Any], instance: dict[str, Any]) -> dict[str, Any]:
    env_config = dict(config.get("environment", {}))
    env_config["image"] = instance["image_name"]
    run_args = list(env_config.get("run_args", ["--rm"]))
    for arg in instance.get("docker_args") or []:
        if arg not in run_args:
            run_args.append(arg)
    platform = instance.get("platform")
    if platform and "--platform" not in run_args:
        run_args.extend(["--platform", platform])
    if instance.get("representation_skill_enabled"):
        mount = (
            f"{instance['representation_skill_host_dir']}:"
            f"/workspace/skills/{instance['representation_skill_name']}:ro"
        )
        if mount not in run_args:
            run_args.extend(["-v", mount])
    env_config["run_args"] = run_args
    return env_config


def run_startup_commands(env: DockerEnvironment, instance: dict[str, Any], config: dict[str, Any]) -> None:
    startup_commands = list(instance.get("post_startup_commands") or [])
    if startup_command := config.get("run", {}).get("env_startup_command"):
        startup_commands.append(Template(startup_command, undefined=StrictUndefined).render(**instance))
    for command in startup_commands:
        output = env.execute(
            {"command": command},
            timeout=instance.get("post_startup_command_timeout", 30),
        )
        if output["returncode"] != 0:
            raise RuntimeError(f"Startup command failed: {output}")


def write_prediction(
    output_dir: Path,
    instance_id: str,
    prediction_model_name: str,
    patch: str,
    traj_path: Path,
) -> None:
    agent = extract_trajectory_metrics(traj_path)
    write_prediction_artifacts(
        output_dir,
        framework="minisweagent",
        instance_id=instance_id,
        model_name=prediction_model_name,
        patch=patch or "",
        agent=agent,
        lock=PRED_LOCK,
        on_corrupt=lambda backup_path: logger.warning(
            "Backed up corrupt predictions file to %s", backup_path
        ),
    )


def process_instance(
    instance: dict[str, Any],
    output_dir: Path,
    config: dict[str, Any],
    *,
    prediction_model_name: str,
    redo_existing: bool,
    consecutive_command_limit: int,
) -> None:
    instance_id = instance["instance_id"]
    instance_dir = output_dir / instance_id
    traj_path = trajectory_path(instance_dir, instance_id)
    if not redo_existing and is_completed_trajectory(traj_path):
        print(f"[{instance_id}] skipping completed trajectory", flush=True)
        redact_json_file(traj_path)
        write_prediction(
            output_dir,
            instance_id,
            prediction_model_name,
            submission_from_trajectory(traj_path),
            traj_path,
        )
        return
    instance_dir.mkdir(parents=True, exist_ok=True)

    env = None
    agent = None
    exit_status = None
    submission = ""
    extra_info: dict[str, Any] = {}

    try:
        model = get_model(config=config.get("model", {}))
        configure_model_abort_exceptions(model)
        env = DockerEnvironment(
            **prepare_env_config(config, instance),
        )
        run_startup_commands(env, instance, config)
        agent_config = dict(config.get("agent", {}))
        agent_config.setdefault("output_path", traj_path)
        agent = ProgressAgent(
            model,
            env,
            instance_id=instance_id,
            consecutive_command_limit=consecutive_command_limit,
            **agent_config,
        )
        info = agent.run(
            instance["problem_statement"],
            feature_goal=instance["feature_goal"],
            acceptance_requirements=instance["acceptance_requirements"],
            public_interface_contract=instance["public_interface_contract"],
            common_task_prompt=instance["common_task_prompt"],
            environment_prompt=instance["environment_prompt"],
            submit_prompt=instance["submit_prompt"],
        )
        exit_status = info.get("exit_status")
        submission = info.get("submission") or ""
        if exit_status == "RepeatedCommandLoop":
            extra_info = {
                key: info[key]
                for key in ("repeated_command", "consecutive_count", "consecutive_command_limit")
                if key in info
            }
    except Exception as exc:
        logger.error(f"Error processing instance {instance_id}: {exc}", exc_info=True)
        exit_status = type(exc).__name__
        extra_info = {"traceback": traceback.format_exc(), "exception_str": str(exc)}
    finally:
        if agent is not None:
            agent.save(
                traj_path,
                {
                    "info": {
                        "exit_status": exit_status,
                        "submission": submission,
                        **extra_info,
                    },
                    "instance_id": instance_id,
                },
            )
            redact_json_file(traj_path)
            annotate_summary(
                instance_dir,
                framework="minisweagent",
                instance_id=instance_id,
                agent=extract_trajectory_metrics(traj_path),
            )
        else:
            write_trajectory(
                traj_path,
                {
                    "info": {
                        "exit_status": exit_status,
                        "submission": submission,
                        **extra_info,
                    },
                },
            )
            annotate_summary(
                instance_dir,
                framework="minisweagent",
                instance_id=instance_id,
                agent=default_agent_metrics(),
            )
        if env is not None:
            env.cleanup()
        write_prediction(output_dir, instance_id, prediction_model_name, submission, traj_path)
        status_label = "finished" if is_completed_trajectory(traj_path) else "failed"
        print(f"[{instance_id}] {status_label}: {exit_status}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run mini-SWE-agent on benchmark instances.")
    parser.add_argument("--instances", type=Path, default=DEFAULT_INSTANCES)
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--prompt-config",
        type=Path,
        default=DEFAULT_PROMPT_CONFIG,
        help="mini-SWE-agent prompt/agent config. Ignored when --config is provided.",
    )
    parser.add_argument(
        "--model-config",
        type=Path,
        default=DEFAULT_MODEL_CONFIG,
        help="mini-SWE-agent model config. Ignored when --config is provided.",
    )
    parser.add_argument(
        "-c",
        "--config",
        action="append",
        default=None,
        help="Additional raw mini-SWE-agent config file(s). Overrides --prompt-config/--model-config when provided.",
    )
    parser.add_argument("-m", "--model", default=None)
    parser.add_argument("--num-workers", "--workers", dest="workers", type=int, default=1)
    parser.add_argument("--num-worksers", dest="workers", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--filter", default=None, help="Regex over instance_id.")
    parser.add_argument("--slice", default=None, help="Python slice syntax, e.g. 0:5.")
    parser.add_argument("--n-limit", type=int, default=None, help="Run the first N selected instances.")
    parser.add_argument("--redo-existing", action="store_true")
    parser.add_argument(
        "--consecutive-command-limit",
        type=int,
        default=6,
        help="Fail an instance after the same bash command is emitted this many times consecutively. Use 0 to disable.",
    )
    parser.add_argument(
        "--enable-representation-skill",
        action="store_true",
        help="Expose the RQ4 representation-equivalence skill registry and let the agent decide whether to load it.",
    )
    parser.add_argument(
        "--representation-skill",
        type=Path,
        default=DEFAULT_REPRESENTATION_SKILL,
        help="Path to the representation-equivalence SKILL.md file.",
    )
    parser.add_argument(
        "--skill-prompt-template",
        type=Path,
        default=DEFAULT_SKILL_PROMPT,
        help="Jinja template used to announce available local skills to the agent.",
    )
    return parser.parse_args()


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


def base_model_name(model_name: str) -> str:
    return artifact_model_name(model_name)


def model_source_from_config(config: dict[str, Any]) -> str:
    if source := config.get("_model_source"):
        return str(source)
    model_name = config.get("model", {}).get("model_name", "")
    if isinstance(model_name, str):
        model_kwargs = config.get("model", {}).get("model_kwargs", {}) or {}
        if model_name.startswith("openai/deepseek") or model_kwargs.get("api_base") == "https://api.deepseek.com":
            return "deepseek"
        model_class = str(config.get("model", {}).get("model_class") or "")
        api_base = str(model_kwargs.get("api_base") or "")
        if (
            model_name.startswith(("vertex_ai/", "vertex/"))
            or "aiplatform.googleapis.com" in api_base
        ):
            return "vertex"
        if model_class.startswith("openrouter") or model_name.startswith("openrouter/"):
            return "openrouter"
        if model_name.startswith("dashscope/") or "dashscope.aliyuncs.com" in api_base:
            return "dashscope"
    return ""


def prediction_model_name_from_config(config: dict[str, Any]) -> str:
    configured_name = config.get("prediction_model_name")
    if configured_name:
        return artifact_model_name(configured_name)

    model_name = config.get("model", {}).get("model_name", "")
    if not isinstance(model_name, str):
        return ""
    return artifact_model_name(model_name)


def load_env_value(name: str, *, default: str | None = None) -> str | None:
    if value := os.getenv(name):
        return value
    if value := read_zshrc_export(name):
        os.environ[name] = value
        return value
    if default is not None:
        os.environ[name] = default
        return default
    return None


def configure_model_env(config: dict[str, Any]) -> None:
    model_name = config.get("model", {}).get("model_name", "")
    if not isinstance(model_name, str):
        return
    source = model_source_from_config(config)
    model_retries = config.get("model", {}).get("max_retries")
    if source == "deepseek" and model_retries is not None:
        # mini-SWE-agent's LiteLLM retry helper counts total attempts, while
        # our config field follows the Vertex adapter and counts retries.
        os.environ["MSWEA_MODEL_RETRY_STOP_AFTER_ATTEMPT"] = str(int(model_retries) + 1)

    if source == "deepseek":
        key = os.getenv("DEEPSEEK_API_KEY")
        if not key and (key := read_zshrc_export("DEEPSEEK_API_KEY")):
            os.environ["DEEPSEEK_API_KEY"] = key
        if key:
            model_config = config.setdefault("model", {})
            model_kwargs = dict(model_config.get("model_kwargs", {}))
            model_kwargs["api_key"] = key
            model_config["model_kwargs"] = model_kwargs
    elif source == "vertex":
        load_env_value("GoogleVertaxAI_API_KEY")
        load_env_value("GoogleProjectID")
    elif source == "openrouter":
        load_env_value("OPENROUTER_API_KEY")
    elif source == "dashscope":
        key = load_env_value("DASHSCOPE_API_KEY")
        if key:
            model_config = config.setdefault("model", {})
            model_kwargs = dict(model_config.get("model_kwargs", {}))
            model_kwargs["api_key"] = key
            model_config["model_kwargs"] = model_kwargs


def configure_model_abort_exceptions(model: Any) -> None:
    abort_exceptions = getattr(model, "abort_exceptions", None)
    if not isinstance(abort_exceptions, list):
        return
    try:
        import litellm
    except ImportError:
        return
    bad_request_error = litellm.exceptions.BadRequestError
    if bad_request_error not in abort_exceptions:
        abort_exceptions.append(bad_request_error)


def print_model_env_diagnostic(config: dict[str, Any]) -> None:
    model_name = config.get("model", {}).get("model_name", "")
    source = model_source_from_config(config)
    key_name = {
        "deepseek": "DEEPSEEK_API_KEY",
        "vertex": "GoogleVertaxAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "dashscope": "DASHSCOPE_API_KEY",
        "siliconflow": "SILICONFLOW_API_KEY",
    }.get(source)
    key = os.getenv(key_name or "") or ""
    fingerprint = hashlib.sha256(key.encode()).hexdigest()[:8] if key else "none"
    last4 = key[-4:] if key else "none"
    suffix = ""
    if source == "vertex":
        project = os.getenv("GoogleProjectID") or ""
        model_config = config.get("model", {})
        location = model_config.get("location", "")
        api_base = ((model_config.get("model_kwargs") or {}).get("api_base") or "")
        if not location and "/locations/" in api_base:
            location = api_base.split("/locations/", 1)[1].split("/", 1)[0]
        suffix = (
            f"; project_visible={bool(project)} project_len={len(project)} "
            f"location={location or 'none'}"
        )
    elif source in {"dashscope", "siliconflow"}:
        api_base = ((config.get("model", {}).get("model_kwargs") or {}).get("api_base") or "")
        suffix = f"; api_base={api_base or 'default'}"
    print(
        f"Model config: {model_name} source={source}; {key_name or 'api_key'} visible={bool(key)} "
        f"len={len(key)} last4={last4} fingerprint={fingerprint}{suffix}",
        flush=True,
    )


def _redact_proxy_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
    except ValueError:
        return "<invalid>"
    if not parsed.scheme or not parsed.netloc:
        return "<set>"
    host = parsed.hostname or ""
    netloc = host
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunsplit((parsed.scheme, netloc, "", "", ""))


def print_proxy_env_diagnostic() -> None:
    entries = []
    for name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY", "NO_PROXY"):
        value = os.getenv(name) or os.getenv(name.lower()) or ""
        if value:
            entries.append(f"{name}={_redact_proxy_url(value)}")
    print(f"Proxy env: {'; '.join(entries) if entries else 'none'}", flush=True)


def main() -> None:
    args = parse_args()
    if args.n_limit is not None and args.n_limit > 0:
        if args.slice:
            raise ValueError("Use either --slice or --n-limit, not both")
        args.slice = f"0:{args.n_limit}"
    config_specs = args.config or [str(args.prompt_config), str(args.model_config)]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    add_file_handler(args.output_dir / "minisweagent.log")
    config = load_config(config_specs, args.model)
    prediction_model_name = prediction_model_name_from_config(config)
    configure_model_env(config)
    print_model_env_diagnostic(config)
    print_proxy_env_diagnostic()
    print(f"Prediction model label: {prediction_model_name}", flush=True)
    instances = [normalize_instance(row) for row in read_jsonl(args.instances)]
    instances = enrich_instances_with_task_fields(instances, args.samples_dir)
    instances = filter_by_instance_id(instances, args.filter, args.slice)
    if args.enable_representation_skill:
        if not args.representation_skill.exists():
            raise FileNotFoundError(f"Representation skill not found: {args.representation_skill}")
        if not args.skill_prompt_template.exists():
            raise FileNotFoundError(f"Skill prompt template not found: {args.skill_prompt_template}")
        instances = enable_representation_skill_for_instances(
            instances,
            skill_path=args.representation_skill.resolve(),
            skill_prompt_template=args.skill_prompt_template.resolve(),
        )
    print(f"Running {len(instances)} instances. Output: {args.output_dir}", flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                process_instance,
                instance,
                args.output_dir,
                config,
                prediction_model_name=prediction_model_name,
                redo_existing=args.redo_existing,
                consecutive_command_limit=args.consecutive_command_limit,
            )
            for instance in instances
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()


if __name__ == "__main__":
    main()
