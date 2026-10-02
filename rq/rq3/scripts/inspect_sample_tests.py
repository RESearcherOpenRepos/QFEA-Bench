"""Print exact-patch test bodies while manually reviewing constraint labels.

The test sources must be staged at /tmp/qfea-test-sources/<sample_id>/<test path>.
Run from the repository root with a dataset ID, for example:
    python3 rq/rq3/scripts/inspect_sample_tests.py 11
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOT = Path("/tmp/qfea-test-sources")


def test_node(source: str, selector: str) -> ast.FunctionDef | ast.AsyncFunctionDef:
    parts = selector.split("::")[1:]
    parts[-1] = parts[-1].split("[", 1)[0]
    tree = ast.parse(source)
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
    nodes = tree.body
    current_class = None
    for part in parts:
        matches = [
            node for node in nodes
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == part
        ]
        if len(matches) > 1 and all(isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) for n in matches):
            # Repeated definitions in one lexical body bind the last definition.
            # Tequila's test_h2_hamiltonian_psi4 is rebound to its PySCF test.
            matches = matches[-1:]
        if not matches:
            # ddt expands @data methods into names with encoded argument suffixes.
            matches = [
                node for node in nodes
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and part.startswith(node.name + "_")
            ]
            if matches:
                longest = max(len(node.name) for node in matches)
                matches = [node for node in matches if len(node.name) == longest]
        if not matches and current_class is not None:
            # Selected unittest methods may be inherited from a base class in
            # the same test file. Resolve source only; no label is inferred.
            pending = [base.id for base in current_class.bases if isinstance(base, ast.Name)]
            visited = set()
            while pending and not matches:
                base_name = pending.pop(0)
                if base_name in visited or base_name not in classes:
                    continue
                visited.add(base_name)
                base_class = classes[base_name]
                matches = [
                    member for member in base_class.body
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and member.name == part
                ]
                pending.extend(base.id for base in base_class.bases if isinstance(base, ast.Name))
        if len(matches) != 1:
            raise ValueError(f"Cannot locate {part} within {selector}")
        node = matches[0]
        nodes = node.body
        if isinstance(node, ast.ClassDef):
            current_class = node
    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        raise ValueError(f"Not a function: {selector}")
    return node


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id", type=int)
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    index = json.loads((ROOT / "benchmark/dataset/samples/index.json").read_text())
    item = index["samples"][args.id - 1]
    if item["id"] != args.id:
        raise ValueError("Dataset index order differs from sample ID")
    sample = json.loads(
        (ROOT / "benchmark/dataset/samples" / item["sample_path"] / "sample.json").read_text()
    )
    print(f"ID {args.id}: {item['sample_id']} ({item['repo']})")
    print("TASK:", sample["task"]["problem_statement"])
    for requirement in sample["task"].get("requirements", []):
        print("REQUIREMENT:", requirement)
    test_number = 0
    for split, key in (("F2P", "fail_pass"), ("P2P", "pass_pass")):
        for selector in sample["validation"]["patched"][key]["file_list"]:
            test_number += 1
            path = SOURCE_ROOT / item["sample_id"] / selector.split("::")[0]
            source = path.read_text()
            node = test_node(source, selector)
            lines = source.splitlines()
            start = min((dec.lineno for dec in node.decorator_list), default=node.lineno)
            print(f"\nTEST {test_number} {split} {selector} L{start}-{node.end_lineno}")
            for line_number in range(start, node.end_lineno + 1):
                line = lines[line_number - 1]
                if args.compact:
                    key_line = any(
                        word in line for word in
                        ("assert", "Assert", "raises", "Raises", "return ", "def test_", "@pytest")
                    )
                    if not key_line:
                        continue
                print(f"  {line_number}: {line}")


if __name__ == "__main__":
    main()
