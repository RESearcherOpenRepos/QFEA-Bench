from __future__ import annotations

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
PREPROCESSING_DIR = PROJECT_ROOT / "preprocessing"
LOG_DIR = PREPROCESSING_DIR / "logs"
RESULT_DIR = PREPROCESSING_DIR / "result"

GITHUB_TOKEN_ENV_VARS = [
    "GITHUB_TOKEN_1",
    "GITHUB_TOKEN_2",
    "GITHUB_TOKEN_3",
    "GITHUB_TOKEN_5",
    "GITHUB_TOKEN_6",
]

DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_PER_PAGE = 100

QISKIT_REPO_SEARCH_QUERY = (
    "qiskit language:Python archived:false fork:false "
    "in:name,description,readme"
)

DEFAULT_BENCHMARK_REPOS = [
    "qiskit-community/qiskit-nature",
    "qiskit-community/qiskit-machine-learning",
    "qiskit-community/qiskit-optimization",
]

FEATURE_KEYWORDS = [
    "feat",
    "feature",
    "enhancement",
    "new",
    "add",
    "support",
    "introduce",
    "implement",
]

TEST_PATH_HINTS = (
    "test/",
    "tests/",
    "/test_",
    "_test.py",
)

SOURCE_PATH_EXCLUDES = (
    "docs/",
    ".github/",
    "releasenotes/",
    "requirements",
    "tox.ini",
)


def ensure_runtime_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_DIR.mkdir(parents=True, exist_ok=True)


def get_available_github_tokens() -> list[str]:
    tokens: list[str] = []
    for name in GITHUB_TOKEN_ENV_VARS:
        token = os.getenv(name)
        if token and token not in tokens:
            tokens.append(token)
    return tokens
