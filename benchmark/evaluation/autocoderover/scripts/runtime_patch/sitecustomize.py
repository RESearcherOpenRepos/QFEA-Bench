"""Runtime compatibility patches for QuanBench AutoCodeRover runs.

This module is imported automatically by Python when its directory is on
PYTHONPATH. Keep AutoCodeRover itself unmodified; benchmark-specific provider
compatibility lives here instead.
"""

from __future__ import annotations

import argparse
import functools
import inspect
import json
import os
import re
import sys
import textwrap
from pathlib import Path
from typing import Any


TRUE_VALUES = {"1", "true", "yes", "on"}

SEARCH_TOOL_PROMPT_MARKERS = (
    "you can use the following search APIs",
    "Let's analyze collected context first.",
    "Based on your analysis, answer below questions",
)

SEARCH_API_SPECS = {
    "search_class": (
        "Search for a class in the codebase.",
        (("class_name", "string"),),
    ),
    "search_class_in_file": (
        "Search for a class in a given file.",
        (("class_name", "string"), ("file_name", "string")),
    ),
    "search_method_in_file": (
        "Search for a method in a given file.",
        (("method_name", "string"), ("file_path", "string")),
    ),
    "search_method_in_class": (
        "Search for a method in a given class.",
        (("method_name", "string"), ("class_name", "string")),
    ),
    "search_method": (
        "Search for a method in the entire codebase.",
        (("method_name", "string"),),
    ),
    "search_code": (
        "Search for a code snippet in the entire codebase.",
        (("code_str", "string"),),
    ),
    "search_code_in_file": (
        "Search for a code snippet in a given file.",
        (("code_str", "string"), ("file_path", "string")),
    ),
    "get_code_around_line": (
        "Get the code around a given line in a file.",
        (
            ("file_path", "string"),
            ("line_number", "integer"),
            ("window_size", "integer"),
        ),
    ),
}

SEARCH_API_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": {
                    arg_name: {"type": arg_type} for arg_name, arg_type in arguments
                },
                "required": [arg_name for arg_name, _ in arguments],
            },
        },
    }
    for name, (description, arguments) in SEARCH_API_SPECS.items()
]

SEARCH_API_ARG_ORDER = {
    name: tuple(arg_name for arg_name, _ in arguments)
    for name, (_, arguments) in SEARCH_API_SPECS.items()
}


def enabled(name: str) -> bool:
    return os.getenv(name, "").lower() in TRUE_VALUES


def get_field(value: Any, field_name: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(field_name)
    return getattr(value, field_name, None)


def stringify_content(content: Any) -> str:
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(
                    stringify_content(
                        item.get("text")
                        or item.get("content")
                        or item.get("thinking")
                    )
                )
            else:
                text = getattr(item, "text", None)
                if text is None:
                    text = getattr(item, "content", None)
                if text is None:
                    text = getattr(item, "thinking", None)
                if isinstance(text, str):
                    parts.append(text)
        return "".join(parts)
    return str(content)


def ordered_tool_arguments(
    arguments: dict[str, Any],
    arg_order: tuple[str, ...] | None,
) -> list[Any]:
    if not arg_order:
        return list(arguments.values())

    values: list[Any] = []
    for arg_name in arg_order:
        if arg_name in arguments:
            values.append(arguments[arg_name])
    if len(values) == len(arg_order):
        return values
    return list(arguments.values())


def format_function_call(
    name: str,
    arguments: Any,
    arg_order: tuple[str, ...] | None = None,
) -> str:
    parsed_arguments = arguments
    if isinstance(arguments, str):
        stripped_arguments = arguments.strip()
        if not stripped_arguments:
            parsed_arguments = {}
        else:
            try:
                parsed_arguments = json.loads(stripped_arguments, strict=False)
            except json.JSONDecodeError:
                return f"{name}({stripped_arguments})"

    if isinstance(parsed_arguments, dict):
        values = ordered_tool_arguments(parsed_arguments, arg_order)
    elif isinstance(parsed_arguments, list):
        values = parsed_arguments
    elif parsed_arguments is None:
        values = []
    else:
        values = [parsed_arguments]

    return f"{name}({', '.join(json.dumps(value) for value in values)})"


def stringify_tool_calls(
    tool_calls: Any,
    tool_arg_order: dict[str, tuple[str, ...]] | None = None,
) -> str:
    if not tool_calls:
        return ""

    rendered_calls: list[str] = []
    for tool_call in tool_calls:
        function = get_field(tool_call, "function")
        if function is None:
            name = get_field(tool_call, "name") or get_field(tool_call, "tool_type")
            arguments = get_field(tool_call, "arguments")
            if arguments is None:
                arguments = get_field(tool_call, "args")
        else:
            name = get_field(function, "name")
            arguments = get_field(function, "arguments")

        if not name:
            continue
        rendered_calls.append(
            format_function_call(
                name,
                arguments,
                arg_order=(tool_arg_order or {}).get(name),
            )
        )

    return "\n".join(rendered_calls)


def optional_json_env(name: str) -> dict | None:
    value = os.getenv(name)
    if not value:
        return None
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{name} must contain a JSON object.")
    return parsed


def extract_json_payload(text: str) -> Any | None:
    """Best-effort JSON extraction for provider responses with code fences.

    ACR sometimes asks LiteLLM for json_object responses by pre-filling ``{``.
    Some providers still return fenced JSON, yielding strings like
    ``{```json\n{...}\n````, which are semantically usable but fail strict
    ``json.loads``. This helper keeps the strict path first and only recovers a
    complete JSON object or array from the model response.
    """

    stripped = text.strip()
    if not stripped:
        return None

    candidates = [stripped]
    for match in re.finditer(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL):
        fenced = match.group(1).strip()
        if fenced:
            candidates.append(fenced)

    decoder = json.JSONDecoder()
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

        for index, char in enumerate(candidate):
            if char not in "{[":
                continue
            try:
                payload, _end = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, (dict, list)):
                return payload
    return None


def should_enable_search_tools(model_name: str, messages: list[dict]) -> bool:
    if not enabled("ACR_LITELLM_ENABLE_SEARCH_TOOLS"):
        return False

    # Only the active search prompt should enable native tools. Patch generation
    # can reuse search history when no bug locations were found; scanning the
    # full history would leak search tools into the final patch-writing call.
    for message in reversed(messages):
        if not isinstance(message, dict) or message.get("role") != "user":
            continue
        content = stringify_content(message.get("content"))
        return any(marker in content for marker in SEARCH_TOOL_PROMPT_MARKERS)
    return False


def patch_argparse_model_choices() -> None:
    original = argparse.ArgumentParser.add_argument
    if getattr(original, "_quanbench_acr_model_choices", False):
        return

    @functools.wraps(original)
    def add_argument(self: argparse.ArgumentParser, *args: Any, **kwargs: Any) -> Any:
        if "--model" in args:
            kwargs = dict(kwargs)
            kwargs.pop("choices", None)
        return original(self, *args, **kwargs)

    add_argument._quanbench_acr_model_choices = True
    argparse.ArgumentParser.add_argument = add_argument


def patch_overall_retry_limit() -> None:
    value = os.getenv("ACR_OVERALL_RETRY_LIMIT")
    if not value:
        return
    from app import config

    config.overall_retry_limit = int(value)


def patch_litellm_generic() -> None:
    from app.model import common

    if getattr(common.LiteLLMGeneric, "_quanbench_litellm_generic", False):
        return

    def extract_resp_content(
        self: Any,
        chat_message: Any,
        tool_arg_order: dict[str, tuple[str, ...]] | None = None,
    ) -> str:
        tool_calls = stringify_tool_calls(
            get_field(chat_message, "tool_calls"),
            tool_arg_order=tool_arg_order,
        )
        if tool_arg_order and tool_calls:
            return tool_calls

        content = stringify_content(get_field(chat_message, "content"))
        if content:
            return content

        if tool_calls:
            common.log_and_print(
                "LiteLLM returned empty message.content; using structured tool_calls."
            )
            return tool_calls

        common.log_and_print("LiteLLM returned empty message.content.")
        return ""

    @common.retry(
        wait=common.wait_random_exponential(min=30, max=600),
        stop=common.stop_after_attempt(3),
    )
    def call(
        self: Any,
        messages: list[dict],
        top_p: float = 1,
        tools: Any = None,
        response_format: str = "text",
        **kwargs: Any,
    ) -> tuple[str, float, int, int]:
        try:
            prefill_content = "{"
            tool_arg_order = kwargs.get("tool_arg_order")
            if tools is None and should_enable_search_tools(self.name, messages):
                tools = SEARCH_API_TOOLS
                tool_arg_order = SEARCH_API_ARG_ORDER
            if response_format == "json_object":
                messages.append({"role": "assistant", "content": prefill_content})

            completion_kwargs = {
                "api_key": os.getenv("ACR_LITELLM_API_KEY") or None,
                "api_base": os.getenv("ACR_LITELLM_API_BASE") or None,
                "extra_body": optional_json_env("ACR_LITELLM_EXTRA_BODY"),
                "timeout": int(os.getenv("ACR_LITELLM_TIMEOUT", "300")),
            }
            if tools:
                completion_kwargs["tools"] = tools

            response = common.litellm.completion(
                model=self.name,
                messages=messages,
                temperature=common.MODEL_TEMP,
                max_tokens=int(os.getenv("ACR_TOKEN_LIMIT", "1024")),
                response_format=(
                    {"type": response_format} if "gpt" in self.name else None
                ),
                top_p=top_p,
                stream=False,
                **completion_kwargs,
            )
            assert isinstance(response, common.ModelResponse)
            resp_usage = response.usage
            assert resp_usage is not None
            input_tokens = int(resp_usage.prompt_tokens)
            output_tokens = int(resp_usage.completion_tokens)
            cost = self.calc_cost(input_tokens, output_tokens)

            common.thread_cost.process_cost += cost
            common.thread_cost.process_input_tokens += input_tokens
            common.thread_cost.process_output_tokens += output_tokens

            first_resp_choice = response.choices[0]
            assert isinstance(first_resp_choice, common.Choices)
            resp_msg = first_resp_choice.message
            content = self.extract_resp_content(
                resp_msg,
                tool_arg_order=tool_arg_order,
            )
            if not content:
                common.log_and_print(
                    "LiteLLM returned empty content "
                    f"(finish_reason={getattr(first_resp_choice, 'finish_reason', None)})."
                )
            if response_format == "json_object" and not content.startswith(
                prefill_content
            ):
                content = prefill_content + content

            return content, cost, input_tokens, output_tokens

        except common.BadRequestError as exc:
            if exc.code == "context_length_exceeded":
                common.log_and_print("Context length exceeded")
            raise exc

    def set_model(model_name: str) -> None:
        if model_name not in common.MODEL_HUB and not model_name.startswith(
            "litellm-generic-"
        ):
            print(f"Invalid model name: {model_name}")
            sys.exit(1)
        if model_name.startswith("litellm-generic-"):
            real_model_name = model_name.removeprefix("litellm-generic-")
            try:
                input_cost, output_cost = common.cost_per_token(
                    model=real_model_name,
                    prompt_tokens=5,
                    completion_tokens=10,
                )
            except Exception:
                input_cost = 0.0
                output_cost = 0.0
            common.SELECTED_MODEL = common.LiteLLMGeneric(
                real_model_name,
                input_cost,
                output_cost,
            )
        else:
            common.SELECTED_MODEL = common.MODEL_HUB[model_name]
        common.SELECTED_MODEL.setup()

    common.LiteLLMGeneric.extract_resp_content = extract_resp_content
    common.LiteLLMGeneric.call = call
    common.set_model = set_model
    common.LiteLLMGeneric._quanbench_litellm_generic = True


def patch_json_response_recovery() -> None:
    from app import post_process

    if getattr(post_process.is_valid_json, "_quanbench_json_recovery", False):
        return

    original = post_process.is_valid_json

    @functools.wraps(original)
    def is_valid_json(json_str: str) -> tuple[Any, list | dict | None]:
        status, data = original(json_str)
        if status == post_process.ExtractStatus.IS_VALID_JSON:
            return status, data

        recovered = extract_json_payload(json_str)
        if recovered is None:
            return status, data
        return post_process.ExtractStatus.IS_VALID_JSON, recovered

    is_valid_json._quanbench_json_recovery = True
    post_process.is_valid_json = is_valid_json


def patch_agent_proxy_json_output() -> None:
    from app import post_process
    from app.agents import agent_proxy

    if getattr(agent_proxy.run_with_retries, "_quanbench_json_output", False):
        return

    def run_with_retries(text: str, retries: int = 5) -> tuple[str | None, list[Any]]:
        msg_threads = []
        for idx in range(1, retries + 1):
            agent_proxy.logger.debug(
                "Trying to convert API calls/bug locations into json. Try {} of {}.",
                idx,
                retries,
            )

            res_text, new_thread = agent_proxy.run(text)
            msg_threads.append(new_thread)

            extract_status, data = post_process.is_valid_json(res_text)
            if extract_status != post_process.ExtractStatus.IS_VALID_JSON:
                agent_proxy.logger.debug("Invalid json. Will retry.")
                continue

            valid, diagnosis = agent_proxy.is_valid_response(data)
            if not valid:
                agent_proxy.logger.debug(f"{diagnosis}. Will retry.")
                continue

            agent_proxy.logger.debug("Extracted a valid json.")
            return json.dumps(data, ensure_ascii=False), msg_threads
        return None, msg_threads

    run_with_retries._quanbench_json_output = True
    agent_proxy.run_with_retries = run_with_retries


def patch_lint_python_content() -> None:
    from app.agents import patch_utils

    if getattr(patch_utils.lint_python_content, "_quanbench_lint_python_content", False):
        return

    def lint_python_content(content: str) -> bool:
        pylint_out = patch_utils.Writable()
        reporter = patch_utils.TextReporter(pylint_out)

        with patch_utils.NamedTemporaryFile(buffering=0) as handle:
            handle.write(content.encode())
            patch_utils.Run(
                ["--rcfile", os.devnull, "--errors-only", handle.name],
                reporter=reporter,
                exit=False,
            )

        return not any(error.endswith("(syntax-error)") for error in pylint_out.content)

    lint_python_content._quanbench_lint_python_content = True
    patch_utils.lint_python_content = lint_python_content


def _strip_workspace_repo_prefix(path: Path) -> Path | None:
    parts = path.parts
    marker = ("workspace", "repo")
    for index in range(0, len(parts) - len(marker)):
        if parts[index : index + len(marker)] != marker:
            continue
        suffix = parts[index + len(marker) :]
        if suffix:
            return Path(*suffix)
    return None


def _quanbench_normalize_new_file_target(target_file: str, repo_path: str) -> Path | None:
    target_path = Path(target_file)
    repo_root = Path(repo_path).resolve()
    normalized: Path | None

    if target_path.is_absolute():
        try:
            normalized = target_path.resolve().relative_to(repo_root)
        except ValueError:
            normalized = _strip_workspace_repo_prefix(target_path)
    else:
        normalized = _strip_workspace_repo_prefix(target_path) or target_path

    if normalized is None or not normalized.parts or normalized == Path("."):
        return None
    if normalized.is_absolute() or ".." in normalized.parts:
        return None
    return normalized


def patch_post_process_new_file_edits() -> None:
    from app import post_process

    if getattr(
        post_process.convert_response_to_diff,
        "_quanbench_new_file_edits",
        False,
    ):
        return

    post_process._quanbench_normalize_new_file_target = _quanbench_normalize_new_file_target

    source = textwrap.dedent(inspect.getsource(post_process.convert_response_to_diff))
    source = source.replace(
        "        unmatched_edit_indexes = []\n"
        "        for idx, edit in enumerate(edits):\n",
        "        unmatched_edit_indexes = []\n"
        "        created_file_indexes = set()\n"
        "        for idx, edit in enumerate(edits):\n",
        1,
    )
    source = source.replace(
        "            if found_file is None:\n"
        "                unmatched_edit_indexes.append(idx)\n"
        "                continue\n",
        "            if found_file is None:\n"
        "                target_path = _quanbench_normalize_new_file_target(target_file, repo_path)\n"
        "                if not edit.before.strip() and target_path is not None:\n"
        "                    new_file = target_path\n"
        "                    new_file.parent.mkdir(parents=True, exist_ok=True)\n"
        "                    new_file.write_text(edit.after.rstrip(\"\\n\") + \"\\n\")\n"
        "                    apputils.run_command(\n"
        "                        [\"git\", \"add\", \"-N\", str(target_path)],\n"
        "                        stdout=subprocess.DEVNULL,\n"
        "                        stderr=subprocess.DEVNULL,\n"
        "                    )\n"
        "                    created_file_indexes.add(idx)\n"
        "                else:\n"
        "                    unmatched_edit_indexes.append(idx)\n"
        "                continue\n",
        1,
    )
    source = source.replace(
        "        edits_with_empty_before = [\n"
        "            str(idx + 1) for idx, edit in enumerate(edits) if not edit.before.strip()\n"
        "        ]\n",
        "        edits_with_empty_before = [\n"
        "            str(idx + 1)\n"
        "            for idx, edit in enumerate(edits)\n"
        "            if not edit.before.strip() and idx not in created_file_indexes\n"
        "        ]\n",
        1,
    )

    namespace: dict[str, Any] = {}
    exec(source, post_process.__dict__, namespace)
    patched = namespace["convert_response_to_diff"]
    patched._quanbench_new_file_edits = True
    post_process.convert_response_to_diff = patched


def patch_literal_project_paths() -> None:
    """Keep glob metacharacters in the workspace path literal during indexing."""
    import glob
    from os.path import join
    from app.search import search_utils

    def find_python_files(dir_path: str) -> list[str]:
        files = glob.glob(join(glob.escape(dir_path), "**/*.py"), recursive=True)
        return [
            path for path in files
            if not search_utils.is_test_file(path[len(dir_path) + 1 :])
        ]

    search_utils.find_python_files = find_python_files


def apply_patches() -> None:
    patch_argparse_model_choices()
    patch_overall_retry_limit()
    patch_litellm_generic()
    patch_json_response_recovery()
    patch_agent_proxy_json_output()
    patch_lint_python_content()
    patch_post_process_new_file_edits()
    patch_literal_project_paths()


try:
    apply_patches()
except Exception as exc:
    print(f"QuanBench ACR runtime patch failed: {exc}", file=sys.stderr)
    raise
