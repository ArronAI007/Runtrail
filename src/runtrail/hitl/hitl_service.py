from runtrail.hitl.annotation import Annotation
from runtrail.storage.base import BaseStore


class HITLService:
    """Queues uncertain evaluation cases for human review, and records their
    annotations back into the same store (`Report.uncertain_cases()` is the
    usual source of `cases`).
    """

    def __init__(self, store: BaseStore):
        self.store = store

    def enqueue_for_review(self, cases: list[dict]) -> list[str]:
        return [
            self.store.enqueue_review(case=c["case"], output=c["output"], evaluation=c["evaluation"])
            for c in cases
        ]

    def pending_reviews(self) -> list[dict]:
        return self.store.list_pending_reviews()

    def submit_annotation(self, annotation: Annotation) -> None:
        self.store.record_annotation(
            annotation.review_id,
            {
                "reviewer": annotation.reviewer,
                "passed": annotation.passed,
                "score": annotation.score,
                "notes": annotation.notes,
            },
        )
