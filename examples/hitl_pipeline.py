"""Route uncertain evaluation cases to a human reviewer, then submit an annotation."""

from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset
from runtrail.hitl.annotation import Annotation
from runtrail.hitl.hitl_service import HITLService
from runtrail.storage import SQLiteStore


def my_agent(task_input: str) -> dict:
    return {"output": task_input}


if __name__ == "__main__":
    store = SQLiteStore("hitl_example.db")
    dataset = InMemoryDataset([{"input": "is this review positive?", "ground_truth": "yes"}])

    report = Harness(store=store).run(agent=my_agent, dataset=dataset, evaluator=SimpleEvaluator())

    hitl = HITLService(store=store)
    review_ids = hitl.enqueue_for_review(report.uncertain_cases())
    print(f"queued {len(review_ids)} case(s) for review: {review_ids}")

    for review_id in review_ids:
        hitl.submit_annotation(
            Annotation(review_id=review_id, reviewer="alice", passed=True, score=1.0, notes="looks fine")
        )

    print(f"pending reviews after annotation: {len(hitl.pending_reviews())}")
