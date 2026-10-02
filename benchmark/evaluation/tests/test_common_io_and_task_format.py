from __future__ import annotations

import json

from benchmark.evaluation.common.io_utils import (
    filter_by_instance_id,
    parse_slice_spec,
    read_json,
    read_json_safely,
    read_jsonl,
)
from benchmark.evaluation.common.task_format import (
    format_interface_contract,
    format_requirements,
)


def test_common_json_helpers(tmp_path) -> None:
    json_path = tmp_path / "payload.json"
    json_path.write_text(json.dumps({"a": 1}), encoding="utf-8")
    jsonl_path = tmp_path / "payload.jsonl"
    jsonl_path.write_text('{"a": 1}\n\n{"b": 2}\n', encoding="utf-8")
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("{", encoding="utf-8")

    assert read_json(json_path) == {"a": 1}
    assert read_jsonl(jsonl_path) == [{"a": 1}, {"b": 2}]
    assert read_json_safely(bad_path) is None


def test_filter_by_instance_id_matches_existing_runner_semantics() -> None:
    rows = [
        {"instance_id": "openfermion_1"},
        {"instance_id": "pennylane_2"},
        {"instance_id": "qiskit_3"},
        {"instance_id": "qiskit_4"},
    ]

    assert parse_slice_spec("1:3") == slice(1, 3)
    assert filter_by_instance_id(rows, "qiskit", "0:1") == [{"instance_id": "qiskit_3"}]
    assert filter_by_instance_id(rows, None, ":2") == rows[:2]


def test_task_format_preserves_runner_variants() -> None:
    interface = [
        {
            "Type": " Function ",
            "Name": " Foo ",
            "Path": "pkg/module.py",
            "Description": "Do the thing.",
        }
    ]

    assert format_requirements(["A", "B"]) == "1. A\n2. B"
    assert format_requirements([]) == "(No explicit acceptance requirements were provided.)"
    assert format_interface_contract(interface, code_spans=True, strip_names=True) == (
        "1. `Function` `Foo`\n"
        "   - Path: pkg/module.py\n"
        "   - Description: Do the thing."
    )
    assert format_interface_contract(interface, code_spans=False, strip_names=False) == (
        "1.  Function   Foo \n"
        "   - Path: pkg/module.py\n"
        "   - Description: Do the thing."
    )
    assert format_interface_contract([]) == "(No explicit public interface contract was provided.)"
