"""Keep confirmed validation counts distinct from retained execution records."""

from typing import Any


def evaluation_repeat_metadata(result: dict[str, Any]) -> dict[str, Any]:
    """Honor explicit author confirmation without inventing per-run evidence."""
    if result.get("skipped_evaluation"):
        count, source = 0, "skipped_evaluation"
    elif result.get("evaluation_repeats_source") == "author_confirmation":
        count = result.get("evaluation_repeats")
        if type(count) is not int or count < 1:
            raise ValueError("Author-confirmed evaluation_repeats must be a positive integer")
        source = "author_confirmation"
    elif result.get("eval_runs"):
        count, source = len(result["eval_runs"]), "eval_runs"
    else:
        count, source = 1, "single_result"
    return {"evaluation_repeats": count, "evaluation_repeats_source": source}
