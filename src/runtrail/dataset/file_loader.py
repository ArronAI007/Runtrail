import json
from collections.abc import Iterator
from pathlib import Path

from runtrail.dataset.base import BaseDataset


class FileDataset(BaseDataset):
    """Loads task cases from a local JSONL file — one JSON object per line."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def __iter__(self) -> Iterator[dict]:
        with self.path.open() as f:
            for line in f:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def __len__(self) -> int:
        with self.path.open() as f:
            return sum(1 for line in f if line.strip())
