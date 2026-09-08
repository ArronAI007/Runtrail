from collections.abc import Iterator

from runtrail.dataset.base import BaseDataset


class InMemoryDataset(BaseDataset):
    """Wraps a list[dict] of task cases already loaded in memory."""

    def __init__(self, cases: list[dict]):
        self._cases = cases

    def __iter__(self) -> Iterator[dict]:
        return iter(self._cases)

    def __len__(self) -> int:
        return len(self._cases)
