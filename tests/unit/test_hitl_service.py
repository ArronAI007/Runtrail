from runtrail import Harness, SimpleEvaluator
from runtrail.dataset import InMemoryDataset
from runtrail.hitl.annotation import Annotation
from runtrail.hitl.hitl_service import HITLService
from runtrail.storage.sqlite_store import SQLiteStore


def test_enqueue_and_list_pending_reviews(tmp_path):
    store = SQLiteStore(tmp_path / "hitl.db")
    hitl = HITLService(store)

    review_ids = hitl.enqueue_for_review(
        [{"case": {"input": "x"}, "output": {"output": "y"}, "evaluation": {"passed": False}}]
    )

    pending = hitl.pending_reviews()
    assert len(review_ids) == 1
    assert len(pending) == 1
    assert pending[0]["review_id"] == review_ids[0]
    assert pending[0]["case"] == {"input": "x"}


def test_submit_annotation_removes_case_from_pending(tmp_path):
    store = SQLiteStore(tmp_path / "hitl.db")
    hitl = HITLService(store)
    review_id = hitl.enqueue_for_review(
        [{"case": {"input": "x"}, "output": {"output": "y"}, "evaluation": {"passed": False}}]
    )[0]

    hitl.submit_annotation(
        Annotation(review_id=review_id, reviewer="bob", passed=True, score=1.0, notes="fine actually")
    )

    assert hitl.pending_reviews() == []


def test_report_uncertain_cases_feeds_directly_into_hitl_queue(tmp_path):
    def agent(task_input: str) -> dict:
        return {"output": "wrong"}

    dataset = InMemoryDataset([{"input": "x", "ground_truth": "right"}])
    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())

    store = SQLiteStore(tmp_path / "hitl.db")
    review_ids = HITLService(store).enqueue_for_review(report.uncertain_cases())

    assert len(review_ids) == 1
