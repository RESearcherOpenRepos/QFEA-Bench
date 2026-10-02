#!/usr/bin/env python3
"""Create local Python environments after unpacking a QuanBench zip archive."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ROOT_VENV = ROOT / ".venv"
OPENHANDS_BENCHMARKS = ROOT / "external" / "OpenHands-benchmarks"
OPENHANDS_VENV = OPENHANDS_BENCHMARKS / ".venv"

ROOT_REQUIREMENTS = [
    "pytest",
    "matplotlib",
    "numpy",
    "jinja2",
    "pyyaml",
    "requests",
    "docker>=7.1.0",
    "pandas",
    "datasets",
    "unidiff",
    "pexpect",
    "openai",
    "google-genai",
    "litellm",
    "pydantic-settings",
    "python-dotenv",
    "rich",
    "typer",
    "tqdm",
    "swe-rex>=1.4.0",
]

OPENHANDS_LOCAL_PACKAGES = [
    "vendor/software-agent-sdk/openhands-sdk",
    "vendor/software-agent-sdk/openhands-agent-server",
    "vendor/software-agent-sdk/openhands-tools",
    "vendor/software-agent-sdk/openhands-workspace",
    ".",
]


def bin_dir(venv_dir: Path) -> Path:
    return venv_dir / ("Scripts" if os.name == "nt" else "bin")


def python_bin(venv_dir: Path) -> Path:
    return bin_dir(venv_dir) / ("python.exe" if os.name == "nt" else "python")


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def create_venv(venv_dir: Path, python: str, *, force: bool) -> Path:
    current_python = Path(sys.executable).resolve()
    if force and current_python.is_relative_to(venv_dir.resolve()):
        raise RuntimeError(
            f"Refusing to remove the currently running virtualenv: {venv_dir}\n"
            "Run this bootstrap script with a system Python, for example:\n"
            "  python3 benchmark/dataset/scripts/bootstrap_local_envs.py --force"
        )
    if force and venv_dir.exists():
        shutil.rmtree(venv_dir)
    if not venv_dir.exists():
        run([python, "-m", "venv", str(venv_dir)])
    return python_bin(venv_dir)


def pip_install(python: Path, args: list[str], *, cwd: Path = ROOT) -> None:
    run([str(python), "-m", "pip", *args], cwd=cwd)


def ensure_path(path: Path, message: str) -> None:
    if not path.exists():
        raise FileNotFoundError(f"{message}: {path}")


def install_root_env(args: argparse.Namespace) -> None:
    mini_swe_agent = ROOT / "external" / "mini-swe-agent"
    ensure_path(mini_swe_agent / "pyproject.toml", "mini-swe-agent source is missing")

    python = create_venv(ROOT_VENV, args.python, force=args.force)
    pip_install(python, ["install", "-U", "pip", "setuptools", "wheel"])
    pip_install(python, ["install", *ROOT_REQUIREMENTS])
    pip_install(python, ["install", "-e", str(mini_swe_agent)])

    print(f"Root environment ready: {python}", flush=True)


def install_openhands_env(args: argparse.Namespace) -> None:
    ensure_path(OPENHANDS_BENCHMARKS / "pyproject.toml", "OpenHands-benchmarks source is missing")
    for package in OPENHANDS_LOCAL_PACKAGES:
        ensure_path(
            OPENHANDS_BENCHMARKS / package / "pyproject.toml",
            "OpenHands local package is missing",
        )

    python = create_venv(OPENHANDS_VENV, args.openhands_python, force=args.force)
    pip_install(python, ["install", "-U", "pip", "setuptools", "wheel"])
    for package in OPENHANDS_LOCAL_PACKAGES:
        pip_install(python, ["install", "-e", str(OPENHANDS_BENCHMARKS / package)])
    pip_install(python, ["install", "pytest"])

    print(f"OpenHands environment ready: {python}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Rebuild local Python virtualenvs after unpacking this repository on "
            "a different machine. Do not reuse venvs copied from another host."
        )
    )
    parser.add_argument("--python", default="python3", help="Python used for the root .venv.")
    parser.add_argument(
        "--openhands-python",
        default="python3.12",
        help="Python used for external/OpenHands-benchmarks/.venv. OpenHands requires >=3.12.",
    )
    parser.add_argument("--skip-root", action="store_true", help="Do not create the root .venv.")
    parser.add_argument(
        "--skip-openhands",
        action="store_true",
        help="Do not create external/OpenHands-benchmarks/.venv.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Remove existing target venv directories before recreating them.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.skip_root and args.skip_openhands:
        raise SystemExit("Nothing to do: both --skip-root and --skip-openhands were set.")
    if not args.skip_root:
        install_root_env(args)
    if not args.skip_openhands:
        install_openhands_env(args)
    print("All requested environments are ready.", flush=True)


if __name__ == "__main__":
    sys.exit(main())
