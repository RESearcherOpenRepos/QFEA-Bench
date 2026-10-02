#!/usr/bin/env python3
"""Build mini-SWE-agent runtime images from leak-free agent-base images."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from benchmark.evaluation.minisweagent.scripts.export_sweagent_instances import (
    DEFAULT_SAMPLES_DIR,
    adapter_image_name,
)

DEFAULT_WHEELS_DIR = ROOT / ".tmp" / "wheels-linux"
DEFAULT_RUNTIME_IMAGE = "python:3.11-slim"
DEFAULT_RUNTIME_VERSION = "1.4.0"
DEFAULT_WHEEL_INDEX_URL = "https://pypi.tuna.tsinghua.edu.cn/simple"
DEFAULT_WHEEL_EXTRA_INDEX_URL = "https://pypi.org/simple"

DOCKERFILE_TEXT = """\
ARG PYTHON_RUNTIME_IMAGE=python:3.11-slim
ARG BASE_IMAGE=python:3.11-slim
FROM ${PYTHON_RUNTIME_IMAGE} AS swe_rex_runtime
ARG SWE_REX_VERSION=1.4.0
COPY wheels/ /tmp/wheels/
RUN python -m venv /opt/swe-rex-venv \\
    && /opt/swe-rex-venv/bin/python -m pip install --no-cache-dir --upgrade pip \\
    && /opt/swe-rex-venv/bin/python -m pip install --no-cache-dir --no-index --find-links /tmp/wheels "swe-rex==${SWE_REX_VERSION}" \\
    && rm -rf /tmp/wheels

FROM ${BASE_IMAGE}
COPY wheels/ /tmp/wheels/
RUN apt-get update \\
    && apt-get install -y --no-install-recommends iptables \\
    && rm -rf /var/lib/apt/lists/* \\
    && rm -rf /tmp/wheels
COPY --from=swe_rex_runtime /opt/swe-rex-venv /opt/swe-rex-venv
RUN ln -sf /opt/swe-rex-venv/bin/swerex-remote /usr/local/bin/swerex-remote \\
    && command -v swerex-remote
WORKDIR /workspace/repo
ENTRYPOINT []
CMD ["/bin/bash"]
"""


@dataclass(frozen=True)
class RuntimeConfig:
    """Configuration for the isolated agent runtime layer."""

    python_runtime_image: str = DEFAULT_RUNTIME_IMAGE
    swe_rex_version: str = DEFAULT_RUNTIME_VERSION
    wheels_dir: Path = DEFAULT_WHEELS_DIR
    wheel_index_url: str = DEFAULT_WHEEL_INDEX_URL
    wheel_extra_index_url: str | None = DEFAULT_WHEEL_EXTRA_INDEX_URL
    refresh_wheels: bool = False


@dataclass(frozen=True)
class SampleBuildSpec:
    """Per-sample mini runtime build specification."""

    sample_id: str
    base_image: str
    adapter_image: str
    base_commit: str
    patched_commit: str | None


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_sample_files(samples_dir: Path, sample_filter: str | None) -> list[Path]:
    index_path = samples_dir / "index.json"
    if index_path.exists():
        index = read_json(index_path)
        paths = [
            samples_dir / item["sample_path"] / "sample.json"
            for item in index.get("samples", [])
        ]
    else:
        paths = sorted(samples_dir.rglob("sample.json"))
    if sample_filter:
        paths = [path for path in paths if sample_filter in str(path.parent.relative_to(samples_dir))]
    return paths


def load_build_specs(samples_dir: Path, image_prefix: str, sample_filter: str | None) -> list[SampleBuildSpec]:
    specs = []
    for sample_path in iter_sample_files(samples_dir, sample_filter):
        sample = read_json(sample_path)
        instance = sample["instance"]
        sample_id = instance["instance_id"]
        specs.append(
            SampleBuildSpec(
                sample_id=sample_id,
                base_image=f"benchmark-agent-base:{sample_id}",
                adapter_image=adapter_image_name(sample_id, image_prefix),
                base_commit=instance["base_commit"],
                patched_commit=instance.get("patch"),
            )
        )
    return specs


def existing_adapter_images(image_prefix: str) -> set[str]:
    completed = subprocess.run(
        ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        check=True,
        capture_output=True,
        text=True,
    )
    return {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.startswith(image_prefix) and line.endswith(":latest")
    }


def image_workdir(image: str) -> str | None:
    completed = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Config.WorkingDir}}", image],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def current_adapter_images(image_prefix: str, target_workdir: str) -> set[str]:
    return {
        image
        for image in existing_adapter_images(image_prefix)
        if image_workdir(image) == target_workdir
    }


def validate_runtime_config(runtime: RuntimeConfig) -> None:
    if runtime.wheels_dir.exists() and not runtime.wheels_dir.is_dir():
        raise NotADirectoryError(f"Runtime wheel path is not a directory: {runtime.wheels_dir}")


def runtime_wheelhouse_ready(runtime: RuntimeConfig) -> bool:
    pattern = f"swe_rex-{runtime.swe_rex_version}-*.whl"
    return runtime.wheels_dir.exists() and any(runtime.wheels_dir.glob(pattern))


def pip_download_command(runtime: RuntimeConfig) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--dest",
        str(runtime.wheels_dir),
        "--index-url",
        runtime.wheel_index_url,
        "--only-binary=:all:",
        "--platform",
        "manylinux2014_x86_64",
        "--python-version",
        "311",
        "--implementation",
        "cp",
        f"swe-rex=={runtime.swe_rex_version}",
    ]
    if runtime.wheel_extra_index_url:
        command.extend(["--extra-index-url", runtime.wheel_extra_index_url])
    return command


def ensure_runtime_wheels(runtime: RuntimeConfig, dry_run: bool) -> None:
    needs_download = runtime.refresh_wheels or not runtime_wheelhouse_ready(runtime)
    if not needs_download:
        return
    runtime.wheels_dir.mkdir(parents=True, exist_ok=True)
    command = pip_download_command(runtime)
    if dry_run:
        print("Preparing runtime wheelhouse:")
        print(" ".join(command))
        return
    subprocess.run(command, check=True)
    if not runtime_wheelhouse_ready(runtime):
        raise RuntimeError(
            f"Runtime wheelhouse is still incomplete after download: {runtime.wheels_dir}"
        )


def check_docker_available() -> None:
    try:
        subprocess.run(["docker", "version"], check=True, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise RuntimeError("Docker is not installed or not on PATH.") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        detail = f": {stderr}" if stderr else "."
        raise RuntimeError(f"Docker is unavailable{detail}") from exc


def run_preflight(
    samples_dir: Path,
    runtime: RuntimeConfig,
    specs: list[SampleBuildSpec],
    dry_run: bool,
) -> None:
    if not samples_dir.exists():
        raise FileNotFoundError(f"Samples directory does not exist: {samples_dir}")
    validate_runtime_config(runtime)
    ensure_runtime_wheels(runtime, dry_run=dry_run)
    if not dry_run:
        check_docker_available()
    if not specs:
        raise RuntimeError("No samples matched the current filter.")


def docker_build_command(
    spec: SampleBuildSpec,
    runtime: RuntimeConfig,
    context_dir: Path,
) -> list[str]:
    return [
        "docker",
        "build",
        "--platform",
        "linux/amd64",
        "--build-arg",
        f"PYTHON_RUNTIME_IMAGE={runtime.python_runtime_image}",
        "--build-arg",
        f"SWE_REX_VERSION={runtime.swe_rex_version}",
        "--build-arg",
        f"BASE_IMAGE={spec.base_image}",
        "-t",
        spec.adapter_image,
        str(context_dir),
    ]


def build_adapter_image(
    spec: SampleBuildSpec,
    runtime: RuntimeConfig,
    dry_run: bool = False,
) -> None:
    with tempfile.TemporaryDirectory(prefix="quanbench-sweagent-") as tmp:
        context_dir = Path(tmp)
        (context_dir / "Dockerfile").write_text(DOCKERFILE_TEXT, encoding="utf-8")
        shutil.copytree(runtime.wheels_dir, context_dir / "wheels")
        command = docker_build_command(spec, runtime, context_dir)
        if dry_run:
            print(" ".join(command))
            return
        subprocess.run(command, check=True)


def build_images(
    samples_dir: Path,
    image_prefix: str,
    sample_filter: str | None,
    runtime: RuntimeConfig,
    dry_run: bool,
    missing_only: bool,
    current_only: bool,
    target_workdir: str,
) -> list[str]:
    specs = load_build_specs(samples_dir, image_prefix, sample_filter)
    run_preflight(samples_dir, runtime, specs, dry_run=dry_run)
    if missing_only and current_only:
        raise ValueError("--missing-only and --current-only are mutually exclusive")
    if current_only:
        existing = current_adapter_images(image_prefix, target_workdir)
        specs = [spec for spec in specs if spec.adapter_image not in existing]
    elif missing_only:
        existing = existing_adapter_images(image_prefix)
        specs = [spec for spec in specs if spec.adapter_image not in existing]
    built = []
    for spec in specs:
        build_adapter_image(spec, runtime, dry_run=dry_run)
        built.append(spec.adapter_image)
    return built


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build mini-SWE-agent adapter images.")
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--image-prefix", default="benchmark-sweagent-")
    parser.add_argument(
        "--runtime-image",
        default=DEFAULT_RUNTIME_IMAGE,
        help="Python runtime image used only for the isolated agent runtime layer.",
    )
    parser.add_argument(
        "--swe-rex-version",
        default=DEFAULT_RUNTIME_VERSION,
        help="swe-rex version installed into the isolated runtime layer.",
    )
    parser.add_argument(
        "--wheels-dir",
        type=Path,
        default=DEFAULT_WHEELS_DIR,
        help="Cache directory for linux wheels used by the isolated runtime layer.",
    )
    parser.add_argument(
        "--wheel-index-url",
        default=DEFAULT_WHEEL_INDEX_URL,
        help="Primary package index used to prepare runtime wheels.",
    )
    parser.add_argument(
        "--wheel-extra-index-url",
        default=DEFAULT_WHEEL_EXTRA_INDEX_URL,
        help="Optional fallback package index used when the primary mirror is incomplete.",
    )
    parser.add_argument(
        "--refresh-wheels",
        action="store_true",
        help="Re-download the isolated runtime wheels before building adapter images.",
    )
    parser.add_argument("--filter", default=None, help="Only build samples whose id contains this string.")
    parser.add_argument(
        "--missing-only",
        action="store_true",
        help="Skip adapter images that already exist locally.",
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Skip adapter images that already exist locally with the target working directory.",
    )
    parser.add_argument(
        "--target-workdir",
        default="/workspace/repo",
        help="Working directory expected for images skipped by --current-only.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    runtime = RuntimeConfig(
        python_runtime_image=args.runtime_image,
        swe_rex_version=args.swe_rex_version,
        wheels_dir=args.wheels_dir,
        wheel_index_url=args.wheel_index_url,
        wheel_extra_index_url=args.wheel_extra_index_url or None,
        refresh_wheels=args.refresh_wheels,
    )
    built = build_images(
        args.samples_dir,
        args.image_prefix,
        args.filter,
        runtime,
        args.dry_run,
        args.missing_only,
        args.current_only,
        args.target_workdir,
    )
    action = "Prepared" if args.dry_run else "Built"
    print(f"{action} {len(built)} mini-SWE-agent adapter images.")


if __name__ == "__main__":
    main()
