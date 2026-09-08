from runtrail.runtime.checkpoint import Checkpoint


def test_save_and_load_round_trip(tmp_path):
    checkpoint = Checkpoint("run-1", checkpoint_dir=tmp_path)

    checkpoint.save_case("0", {"output": {"output": "a"}, "evaluation": {"passed": True}})
    checkpoint.save_case("1", {"output": {"output": "b"}, "evaluation": {"passed": False}})

    assert checkpoint.completed_case_ids() == ["0", "1"]
    assert checkpoint.load()["1"]["evaluation"]["passed"] is False


def test_load_returns_empty_dict_when_no_checkpoint_exists(tmp_path):
    checkpoint = Checkpoint("missing-run", checkpoint_dir=tmp_path)

    assert checkpoint.load() == {}
    assert checkpoint.completed_case_ids() == []


def test_clear_removes_the_checkpoint_file(tmp_path):
    checkpoint = Checkpoint("run-1", checkpoint_dir=tmp_path)
    checkpoint.save_case("0", {"output": {}, "evaluation": {"passed": True}})

    checkpoint.clear()

    assert checkpoint.load() == {}
