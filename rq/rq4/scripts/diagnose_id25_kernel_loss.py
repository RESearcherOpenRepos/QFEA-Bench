"""Reproduce ID25's two unattributed observations in disposable Docker containers.

Only diagnostic copies are repaired. Saved benchmark predictions remain untouched.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path('/workspace/repo') if '--inside' in sys.argv else Path(__file__).resolve().parents[3]
SID = "qiskit_machine_learning_227_244"
BASE = "26bf303b4a7897ac3f0934d630d236660afa4b98"
GOLD = "93f8cbb3f4f92d40648d616312a4201dedf71113"
IMAGE = "benchmark-evaluation:" + SID
TEST = "test/kernels/algorithms/test_qkernel_trainer.py"
LOSS = "qiskit_machine_learning/utils/loss_functions/kernel_loss_functions.py"
TRAINER = "qiskit_machine_learning/kernels/algorithms/quantum_kernel_trainer.py"
CASES = {"openhands": "glm5_2_20260627", "autocoderover": "deepseek_v4_flash_20260609"}


def inside(case, variant):
    os.chdir("/workspace/repo")
    sys.path.insert(0, str(Path.cwd()))
    output = Path("/audit") / case / variant
    output.mkdir(parents=True, exist_ok=True)
    def git(*args):
        return subprocess.check_output(["git", *args], text=True)
    git("reset", "--hard", GOLD if variant == "reference" else BASE)
    git("clean", "-fd")
    if variant != "reference":
        subprocess.run(["git", "apply", str(Path('/audit') / case / 'submission.patch')], check=True)
        test = Path(TEST)
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text(git("show", GOLD + ":" + TEST))
    if variant == "loss_only":
        path = Path(LOSS)
        old = path.read_text()
        expression = "1.0 - svc.score(kernel_matrix, labels)"
        assert old.count(expression) == 1
        new = old.replace(expression,
            "np.sum(np.abs(svc.dual_coef_[0])) - 0.5 * (svc.dual_coef_[0] @ "
            "kernel_matrix[np.ix_(svc.support_, svc.support_)] @ svc.dual_coef_[0])")
        path.write_text(new)
        import difflib
        (output / "loss_only.patch").write_text("".join(difflib.unified_diff(
            old.splitlines(True), new.splitlines(True), fromfile="a/" + LOSS, tofile="b/" + LOSS)))
    for name, path in [("loss.py", LOSS), ("trainer.py", TRAINER), ("test_qkt.py", TEST)]:
        (output / name).write_text(Path(path).read_text())
    (output / "reference_loss.py").write_text(git("show", GOLD + ":" + LOSS))
    import numpy as np
    import pytest
    from qiskit_machine_learning.utils.loss_functions import SVCLoss
    # ACR uses numpy's global RNG, unlike the test's separately seeded Qiskit RNG.
    # Fix its initial-point randomness for reproducible diagnostic comparisons.
    np.random.seed(10598)
    original = SVCLoss.evaluate
    events = []
    def traced(self, parameter_values, quantum_kernel, data, labels):
        values = np.asarray(parameter_values, dtype=float)
        event = {"parameters": [float(v) if np.isfinite(v) else str(v) for v in values],
                 "finite_parameters": bool(np.isfinite(values).all())}
        events.append(event)
        try:
            value = original(self, parameter_values, quantum_kernel, data, labels)
            event["loss"] = float(value) if np.isfinite(value) else str(value)
            return value
        except Exception as exc:
            event["exception"] = type(exc).__name__ + ": " + str(exc)
            raise
    SVCLoss.evaluate = traced
    code = pytest.main(["-q", "--tb=short", TEST + "::TestQuantumKernelTrainer::test_qkt"])
    result = {"case": case, "variant": variant, "pytest_exit_code": int(code),
              "numpy_seed": 10598, "loss_calls": len(events),
              "nonfinite_parameter_calls": sum(not e["finite_parameters"] for e in events),
              "first_50_losses": [e.get("loss") for e in events[:50]],
              "events": events,
              "test_sha256": hashlib.sha256(Path(TEST).read_bytes()).hexdigest()}
    (output / "trace.json").write_text(json.dumps(result, indent=2) + "\n")
    return 0  # Expected test failures are evidence, not runner failures.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", action="store_true")
    parser.add_argument("--case", choices=list(CASES) + ["reference"])
    parser.add_argument("--variant", choices=["original", "loss_only", "reference"])
    args = parser.parse_args()
    if args.inside:
        return inside(args.case, args.variant)
    output = ROOT / "rq/rq4/results/id25_loss_diagnosis"
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    for case, run in CASES.items():
        source = ROOT / f"benchmark/evaluation/{case}/runs/{run}/preds.json"
        patch = json.loads(source.read_text())["predictions"][SID]["model_patch"]
        folder = output / case
        folder.mkdir(exist_ok=True)
        (folder / "submission.patch").write_text(patch)
        cases.extend((case, variant) for variant in ["original", "loss_only"])
    cases.append(("reference", "reference"))
    results = []
    for case, variant in cases:
        target = output / case / variant
        target.mkdir(parents=True, exist_ok=True)
        command = ["docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64",
                   "--cpus", "2", "--memory", "4g", "-e", "OMP_NUM_THREADS=1",
                   "-e", "OPENBLAS_NUM_THREADS=1", "-e", "QISKIT_PARALLEL=FALSE",
                   "-v", f"{output}:/audit", "-v", f"{Path(__file__).resolve()}:/diagnose.py:ro",
                   "--entrypoint", "python", IMAGE, "/diagnose.py", "--inside", "--case", case,
                   "--variant", variant]
        print("RUN", case, variant, flush=True)
        with (target / "pytest.log").open("w") as log:
            process = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=600)
        if process.returncode:
            raise RuntimeError(f"Runner failed: {target / 'pytest.log'}")
        result = json.loads((target / "trace.json").read_text())
        results.append({k: v for k, v in result.items() if k != "events"})
        print(json.dumps(results[-1]), flush=True)
    (output / "summary.json").write_text(json.dumps(results, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
