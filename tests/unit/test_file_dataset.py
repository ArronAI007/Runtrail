from runtrail.dataset import FileDataset


def test_iterates_jsonl_lines_and_skips_blanks(tmp_path):
    path = tmp_path / "cases.jsonl"
    path.write_text(
        '{"input": "a", "ground_truth": "1"}\n'
        "\n"
        '{"input": "b", "ground_truth": "2"}\n'
    )

    dataset = FileDataset(path)

    assert len(dataset) == 2
    assert list(dataset) == [
        {"input": "a", "ground_truth": "1"},
        {"input": "b", "ground_truth": "2"},
    ]
