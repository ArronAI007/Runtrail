from typer.testing import CliRunner

from runtrail import Harness, SimpleEvaluator
from runtrail.cli import app
from runtrail.dataset import InMemoryDataset

runner = CliRunner()


def _make_report_file(tmp_path, name: str, agent) -> str:
    dataset = InMemoryDataset(
        [
            {"input": "a", "ground_truth": "a"},
            {"input": "b", "ground_truth": "b"},
        ]
    )
    report = Harness().run(agent=agent, dataset=dataset, evaluator=SimpleEvaluator())
    path = tmp_path / name
    report.to_json(path)
    return str(path)


def test_regress_saves_a_baseline(tmp_path):
    good_agent = lambda x: {"output": x}
    report_path = _make_report_file(tmp_path, "baseline.json", good_agent)
    baseline_dir = tmp_path / "baselines"

    result = runner.invoke(
        app, ["regress", "my-suite", report_path, "--save-baseline", "--baseline-dir", str(baseline_dir)]
    )

    assert result.exit_code == 0
    assert "saved baseline" in result.stdout
    assert (baseline_dir / "my-suite.json").exists()


def test_regress_fails_the_process_on_a_real_regression(tmp_path):
    good_agent = lambda x: {"output": x}
    baseline_path = _make_report_file(tmp_path, "baseline.json", good_agent)
    baseline_dir = tmp_path / "baselines"
    runner.invoke(
        app, ["regress", "my-suite", baseline_path, "--save-baseline", "--baseline-dir", str(baseline_dir)]
    )

    broken_agent = lambda x: {"output": "wrong"}
    broken_path = _make_report_file(tmp_path, "broken.json", broken_agent)

    result = runner.invoke(app, ["regress", "my-suite", broken_path, "--baseline-dir", str(baseline_dir)])

    assert result.exit_code == 1
    assert "REGRESSED" in result.stdout


def test_regress_passes_when_no_regression(tmp_path):
    good_agent = lambda x: {"output": x}
    baseline_path = _make_report_file(tmp_path, "baseline.json", good_agent)
    baseline_dir = tmp_path / "baselines"
    runner.invoke(
        app, ["regress", "my-suite", baseline_path, "--save-baseline", "--baseline-dir", str(baseline_dir)]
    )

    same_path = _make_report_file(tmp_path, "same.json", good_agent)

    result = runner.invoke(app, ["regress", "my-suite", same_path, "--baseline-dir", str(baseline_dir)])

    assert result.exit_code == 0


def test_regress_without_a_baseline_exits_with_guidance(tmp_path):
    good_agent = lambda x: {"output": x}
    report_path = _make_report_file(tmp_path, "report.json", good_agent)

    result = runner.invoke(
        app, ["regress", "no-such-suite", report_path, "--baseline-dir", str(tmp_path / "baselines")]
    )

    assert result.exit_code == 1
    assert "no baseline" in result.stdout
