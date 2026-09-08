from typing import Any


def exact_match(output: Any, ground_truth: Any) -> bool:
    return output == ground_truth


def normalized_match(output: Any, ground_truth: Any) -> bool:
    if not isinstance(output, str) or not isinstance(ground_truth, str):
        return exact_match(output, ground_truth)
    return output.strip().lower() == ground_truth.strip().lower()
