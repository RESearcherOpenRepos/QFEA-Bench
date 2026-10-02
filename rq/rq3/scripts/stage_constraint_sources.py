"""Stage selected exact-patch test source files from local evaluation images.

This only extracts source for human review. It does not assign labels.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import tarfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
DEST = Path("/tmp/qfea-test-sources")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-id", type=int, required=True)
    parser.add_argument("--through-id", type=int, required=True)
    args = parser.parse_args()
    index = json.loads((ROOT / "benchmark/dataset/samples/index.json").read_text())["samples"]
    for item in index:
        if not args.from_id <= item["id"] <= args.through_id:
            continue
        sample = json.loads(
            (ROOT / "benchmark/dataset/samples" / item["sample_path"] / "sample.json").read_text()
        )
        paths = sorted({
            selector.split("::")[0]
            for key in ("fail_pass", "pass_pass")
            for selector in sample["validation"]["patched"][key]["file_list"]
        })
        if not paths or any(Path(p).is_absolute() or ".." in Path(p).parts for p in paths):
            raise ValueError(f"Unsafe or missing test paths for ID {item['id']}")
        image = f"benchmark-evaluation:{item['sample_id']}"
        command = [
            "docker", "run", "--rm", "--network", "none", "--platform", "linux/amd64", "--entrypoint", "sh",
            image, "-c", 'git -C /workspace/repo rev-parse HEAD >&2; exec tar -C /workspace/repo -cf - "$@"',
            "--", *paths,
        ]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.stdout is None or proc.stderr is None:
            raise RuntimeError("Docker pipes unavailable")
        found = set()
        with tarfile.open(fileobj=proc.stdout, mode="r|") as archive:
            for member in archive:
                name = member.name.removeprefix("./")
                if name not in paths or not member.isfile():
                    raise ValueError(f"Unexpected archive member: {name}")
                stream = archive.extractfile(member)
                if stream is None:
                    raise ValueError(f"Unreadable archive member: {name}")
                destination = DEST / item["sample_id"] / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(stream.read())
                found.add(name)
        stderr = proc.stderr.read().decode(errors="replace")
        if proc.wait() != 0:
            raise RuntimeError(f"ID {item['id']} Docker extraction failed: {stderr}")
        if stderr.splitlines()[0].strip() != sample["instance"]["patch"]:
            raise ValueError(f"ID {item['id']} image HEAD differs from patch: {stderr}")
        if found != set(paths):
            raise ValueError(f"ID {item['id']} missing source files: {set(paths) - found}")
        print(f"ID {item['id']}: {len(paths)} source files at {sample['instance']['patch']}", flush=True)


if __name__ == "__main__":
    main()
