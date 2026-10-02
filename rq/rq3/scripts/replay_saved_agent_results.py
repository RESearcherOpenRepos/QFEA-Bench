#!/usr/bin/env python3
"""Replay the 15 saved Agent–LLM prediction sets with exact pytest case reports.

Each evaluable saved patch is validated three times. Completed structured outputs
with three recorded or author-confirmed validations are reused. The evaluator never calls an LLM.
Per-setting CSV exports are optional; aggregate scripts read the saved JSON directly.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from benchmark.evaluation.common.evaluation_repeats import evaluation_repeat_metadata

PREDICTIONS_ROOT = ROOT / "benchmark/evaluation"
OUTPUT_DIR = ROOT / "rq/rq3/results/casewise_replays"
EVALUATOR = ROOT / "benchmark/evaluation/scripts/evaluate_agent_preds.py"
SUMMARIZER = ROOT / "rq/rq3/scripts/summarize_structured_constraint_passes.py"
AGENTS = ("minisweagent", "autocoderover", "openhands")
EVALUATION_REPEATS = 3


def complete_casewise(path: Path) -> bool:
    if not path.exists():
        return False
    payload = json.loads(path.read_text())
    results = payload.get("results", [])
    return (
        payload.get("summary", {}).get("pending") == 0
        and len(results) == 106
        and all("test_cases" in result for result in results)
        and all(
            not result.get("timed_out")
            and not result.get("eval_infra_failed")
            and (result.get("skipped_evaluation")
                 or evaluation_repeat_metadata(result)["evaluation_repeats"] == EVALUATION_REPEATS)
            for result in results
        )
    )


def run_logged(command: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as log:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
            log.flush()
        code = process.wait()
    if code:
        raise RuntimeError(f"Command exited {code}: {' '.join(command)}; see {log_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=AGENTS)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--setup-retries", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--export-intermediate", action="store_true",
                        help="Export optional per-setting CSVs to results/intermediate")
    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    agents = (args.agent,) if args.agent else AGENTS
    for agent in agents:
        for predictions in sorted((PREDICTIONS_ROOT / agent / "runs").glob("*/preds.json")):
            run = predictions.parent.name
            output = OUTPUT_DIR / f"{agent}_{run}.json"
            if complete_casewise(output) and not args.force:
                print(f"[reuse] {agent}/{run}: complete structured result", flush=True)
            else:
                print(f"[replay] {agent}/{run}", flush=True)
                run_logged([
                    sys.executable, str(EVALUATOR), str(predictions),
                    "--output", str(output), "--workers", str(args.workers),
                    "--timeout", str(args.timeout),
                    "--setup-retries", str(args.setup_retries),
                    "--stable-runs", str(EVALUATION_REPEATS),
                    *([] if args.force else ["--resume"]),
                ], OUTPUT_DIR / "logs" / f"{agent}_{run}.log")
                if not complete_casewise(output):
                    raise RuntimeError(f"Incomplete structured result: {output}")
            if args.export_intermediate:
                run_logged([
                    sys.executable, str(SUMMARIZER), str(output),
                    "--agent", agent, "--run", run,
                ], OUTPUT_DIR / "logs" / f"{agent}_{run}_summary.log")


if __name__ == "__main__":
    main()
