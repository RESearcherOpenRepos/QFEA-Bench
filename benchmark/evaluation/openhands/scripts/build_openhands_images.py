#!/usr/bin/env python3
"""Build OpenHands agent-server adapter images for benchmark samples."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[4]
OPENHANDS_BENCHMARKS = ROOT / "external" / "OpenHands-benchmarks"
SOFTWARE_AGENT_SDK = OPENHANDS_BENCHMARKS / "vendor" / "software-agent-sdk"
OPENHANDS_VENDOR_PACKAGES = (
    SOFTWARE_AGENT_SDK / "openhands-sdk",
    SOFTWARE_AGENT_SDK / "openhands-agent-server",
    SOFTWARE_AGENT_SDK / "openhands-tools",
    SOFTWARE_AGENT_SDK / "openhands-workspace",
)
DEFAULT_SAMPLES_DIR = ROOT / "benchmark" / "dataset" / "samples"
DEFAULT_BASE_IMAGE_PREFIX = "benchmark-agent-base:"
DEFAULT_IMAGE_PREFIX = "benchmark-openhands-"
AGENT_LAYER_DOCKERFILE = (
    OPENHANDS_BENCHMARKS
    / "benchmarks"
    / "utils"
    / "Dockerfile.agent-layer"
)

sys.path.insert(0, str(OPENHANDS_BENCHMARKS))


def ensure_openhands_vendor_imports() -> None:
    """Make vendored OpenHands SDK packages importable without pip install -e."""
    missing = [
        package
        for package in OPENHANDS_VENDOR_PACKAGES
        if not (package / "openhands").is_dir()
    ]
    if missing:
        formatted = "\n".join(f"  {path}" for path in missing)
        raise RuntimeError(
            "OpenHands vendored SDK packages are missing. Make sure the zip "
            "contains external/OpenHands-benchmarks/vendor/software-agent-sdk "
            "or initialize submodules.\n"
            f"Missing:\n{formatted}"
        )
    for package in reversed(OPENHANDS_VENDOR_PACKAGES):
        package_str = str(package)
        if package_str not in sys.path:
            sys.path.insert(0, package_str)


def reexec_with_openhands_venv() -> None:
    """Prefer the OpenHands-benchmarks venv for OpenHands build helpers."""
    openhands_python = OPENHANDS_BENCHMARKS / ".venv" / "bin" / "python"
    if not openhands_python.exists():
        return
    current = Path(sys.executable)
    target = openhands_python
    if current == target:
        return
    os.execv(str(target), [str(target), *sys.argv])


@dataclass(frozen=True)
class BuildSpec:
    sample_id: str
    base_image: str
    output_image: str


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_sample_files(samples_dir: Path, sample_filter: str | None = None) -> list[Path]:
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
        paths = [
            path
            for path in paths
            if sample_filter in str(path.parent.relative_to(samples_dir))
        ]
    return paths


def image_name(sample_id: str, prefix: str) -> str:
    if prefix.endswith(":"):
        return f"{prefix}{sample_id}"
    return f"{prefix}{sample_id}:latest"


def load_specs(
    samples_dir: Path,
    base_image_prefix: str,
    image_prefix: str,
    sample_filter: str | None,
) -> list[BuildSpec]:
    specs = []
    for sample_path in iter_sample_files(samples_dir, sample_filter):
        sample_id = read_json(sample_path)["instance"]["instance_id"]
        specs.append(
            BuildSpec(
                sample_id=sample_id,
                base_image=image_name(sample_id, base_image_prefix),
                output_image=image_name(sample_id, image_prefix),
            )
        )
    return specs


def local_image_exists(image: str) -> bool:
    completed = subprocess.run(
        ["docker", "image", "inspect", image],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def local_image_workdir(image: str) -> str | None:
    completed = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Config.WorkingDir}}", image],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def local_image_has_command(image: str, command: str) -> bool:
    completed = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "sh",
            image,
            "-lc",
            f"command -v {command} >/dev/null 2>&1",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def retag_local_image(source: str, target: str) -> str:
    completed = subprocess.run(
        ["docker", "tag", source, target],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        output = (completed.stdout + completed.stderr).strip()
        raise RuntimeError(f"Failed to tag {source} as {target}:\n{output}")
    return target


def normalize_builder_image_tag(builder_image: str) -> str:
    if "/" not in builder_image:
        return builder_image
    return retag_local_image(
        builder_image,
        builder_image.replace("/", "-").replace(":", "-") + ":latest",
    )


def docker_pull(image: str) -> bool:
    completed = subprocess.run(
        ["docker", "pull", image],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode == 0:
        return True
    output = (completed.stdout + completed.stderr).strip()
    print(f"Failed to pull {image}; falling back to local build.\n{output}", flush=True)
    return False


def prepare_builder_image(builder_tag: str, build_builder_image) -> str:
    if local_image_exists(builder_tag):
        print(f"Using local OpenHands builder image {builder_tag}", flush=True)
        return normalize_builder_image_tag(builder_tag)
    print(f"Pulling OpenHands builder image {builder_tag}", flush=True)
    if docker_pull(builder_tag):
        return normalize_builder_image_tag(builder_tag)

    builder = build_builder_image(push=False, force_build=True)
    if builder.error or not builder.tags:
        raise RuntimeError(builder.error or "OpenHands builder image produced no tag")
    return normalize_builder_image_tag(builder.tags[0])


def remove_existing_output_images(specs: list[BuildSpec]) -> None:
    images = sorted({spec.output_image for spec in specs if local_image_exists(spec.output_image)})
    for image in images:
        completed = subprocess.run(
            ["docker", "image", "rm", "--force", image],
            text=True,
            capture_output=True,
            check=False,
        )
        output = (completed.stdout + completed.stderr).strip()
        if completed.returncode != 0:
            raise RuntimeError(f"Failed to remove existing image {image}:\n{output}")
        print(f"REMOVED {image}", flush=True)


def check_openhands_benchmarks_ready() -> None:
    if not OPENHANDS_BENCHMARKS.exists():
        raise FileNotFoundError(
            f"OpenHands benchmarks repo not found: {OPENHANDS_BENCHMARKS}"
        )
    sdk_path = OPENHANDS_BENCHMARKS / "vendor" / "software-agent-sdk"
    if not (sdk_path / ".git").exists():
        raise RuntimeError(
            "OpenHands benchmarks submodule is not initialized. Run:\n"
            f"  git -C {OPENHANDS_BENCHMARKS} submodule update --init --recursive"
        )
    if not AGENT_LAYER_DOCKERFILE.exists():
        raise FileNotFoundError(
            f"OpenHands agent layer Dockerfile not found: {AGENT_LAYER_DOCKERFILE}"
        )
    ensure_openhands_vendor_imports()


def assemble_openhands_image(
    base_image: str,
    builder_image: str,
    output_image: str,
    git_sha: str,
) -> tuple[bool, str]:
    command = [
        "docker",
        "build",
        "--file",
        str(AGENT_LAYER_DOCKERFILE),
        "--build-arg",
        f"BASE_IMAGE={base_image}",
        "--build-arg",
        f"BUILDER_IMAGE={builder_image}",
        "--build-arg",
        f"OPENHANDS_BUILD_GIT_SHA={git_sha}",
        "--build-arg",
        "USERNAME=root",
        "--tag",
        output_image,
        str(AGENT_LAYER_DOCKERFILE.parent),
    ]
    env = os.environ.copy()
    env["DOCKER_BUILDKIT"] = "0"
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    output = completed.stdout + completed.stderr
    return completed.returncode == 0, output.strip()


def build_images(specs: list[BuildSpec], skip_existing: bool) -> int:
    return build_images_parallel(
        specs,
        skip_existing=skip_existing,
        jobs=1,
        current_only=False,
        target_workdir="/workspace/repo",
    )


def build_one_image(
    spec: BuildSpec,
    builder_image: str,
    sdk_git_sha: str,
    skip_existing: bool,
    current_only: bool,
    target_workdir: str,
) -> tuple[str, bool, str]:
    if skip_existing and current_only:
        return spec.sample_id, False, "--skip-existing and --current-only are mutually exclusive"
    if (
        current_only
        and local_image_workdir(spec.output_image) == target_workdir
        and local_image_has_command(spec.output_image, "iptables")
    ):
        return spec.sample_id, True, f"{spec.sample_id}: SKIP {spec.output_image}"
    if skip_existing and local_image_exists(spec.output_image):
        return spec.sample_id, True, f"{spec.sample_id}: SKIP {spec.output_image}"
    if not local_image_exists(spec.base_image):
        return (
            spec.sample_id,
            False,
            f"{spec.sample_id}: MISSING base image {spec.base_image}; "
            "build benchmark-agent-base images first",
        )

    ok, output = assemble_openhands_image(
        spec.base_image,
        builder_image,
        spec.output_image,
        sdk_git_sha,
    )
    if ok:
        return spec.sample_id, True, f"{spec.sample_id}: OK {spec.output_image}"
    message = f"{spec.sample_id}: FAIL"
    if output:
        message += f"\n{output}"
    return spec.sample_id, False, message


def build_images_parallel(
    specs: list[BuildSpec],
    skip_existing: bool,
    jobs: int,
    current_only: bool,
    target_workdir: str,
) -> int:
    check_openhands_benchmarks_ready()
    ensure_openhands_vendor_imports()
    from benchmarks.swebench.build_base_images import (
        _get_sdk_submodule_info,
        builder_image_tag,
        build_builder_image,
    )

    builder_image = prepare_builder_image(builder_image_tag(), build_builder_image)
    _, sdk_git_sha, _ = _get_sdk_submodule_info()
    if jobs < 1:
        raise ValueError("--jobs must be at least 1")

    failures = 0
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        futures = [
            executor.submit(
                build_one_image,
                spec,
                builder_image,
                sdk_git_sha,
                skip_existing,
                current_only,
                target_workdir,
            )
            for spec in specs
        ]
        for future in as_completed(futures):
            _, ok, message = future.result()
            if not ok:
                failures += 1
            print(message, flush=True)
    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Layer OpenHands agent-server onto benchmark base-only images."
    )
    parser.add_argument("--samples-dir", type=Path, default=DEFAULT_SAMPLES_DIR)
    parser.add_argument("--base-image-prefix", default=DEFAULT_BASE_IMAGE_PREFIX)
    parser.add_argument("--image-prefix", default=DEFAULT_IMAGE_PREFIX)
    parser.add_argument("--filter", default=None)
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument(
        "--remove-existing",
        action="store_true",
        help=(
            "Remove selected output images before building. Use after rebuilding "
            "benchmark-agent-base:* base images so OpenHands images cannot retain "
            "layers from stale base tags."
        ),
    )
    parser.add_argument(
        "--current-only",
        action="store_true",
        help="Skip images that already exist locally with the target working directory.",
    )
    parser.add_argument(
        "--target-workdir",
        default="/workspace/repo",
        help="Working directory expected for images skipped by --current-only.",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        help="Number of Docker builds to run in parallel. Default: 1.",
    )
    return parser.parse_args()


def main() -> None:
    reexec_with_openhands_venv()
    args = parse_args()
    if args.remove_existing and (args.skip_existing or args.current_only):
        raise ValueError("--remove-existing cannot be combined with --skip-existing or --current-only")
    specs = load_specs(
        args.samples_dir,
        args.base_image_prefix,
        args.image_prefix,
        args.filter,
    )
    if args.remove_existing:
        remove_existing_output_images(specs)
    failures = build_images_parallel(
        specs,
        args.skip_existing,
        args.jobs,
        args.current_only,
        args.target_workdir,
    )
    if failures:
        raise SystemExit(failures)


if __name__ == "__main__":
    main()
