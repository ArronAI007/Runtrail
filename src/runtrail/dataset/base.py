from abc import ABC, abstractmethod
from collections.abc import Iterator


class BaseDataset(ABC):
    """Interface every Dataset (in-memory / file / benchmark adapter) implements."""

    @abstractmethod
    def __iter__(self) -> Iterator[dict]:
        """Yield task cases, each a dict with at least 'input' and optional 'ground_truth'."""

    @abstractmethod
    def __len__(self) -> int:
        ...
