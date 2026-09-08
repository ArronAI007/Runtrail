from typer.testing import CliRunner

from runtrail import Harness, SimpleEvaluator
from runtrail.cli import app
from runtrail.dataset import InMemoryDataset

runner = CliRunner()


def test_report_command_prints_summary_and_failure_breakdown(tmp_path):
    def agent(task_input: str) -> dict:
        if task_input == "bad":
            raise TimeoutError("loop")
        return {"output": task_input, "steps": [{"type": "thought", "content": "x"}]}

    dataset = InMemoryDataset(
        [
            {"input": "ok", "ground_truth": "ok"},
            {"input": "bad", "ground_truth": "y"},
        ]
    )
    generated_report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())
    report_path = tmp_path / "report.json"
    generated_report.to_json(report_path)

    result = runner.invoke(app, ["report", str(report_path)])

    assert result.exit_code == 0
    assert "1/2 passed" in result.stdout
    assert "infinite_loop: 1" in result.stdout
