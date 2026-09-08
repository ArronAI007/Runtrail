from dataclasses import dataclass


@dataclass
class Annotation:
    """One human reviewer's verdict on a queued HITL review."""

    review_id: str
    reviewer: str
    passed: bool
    score: float
    notes: str = ""
