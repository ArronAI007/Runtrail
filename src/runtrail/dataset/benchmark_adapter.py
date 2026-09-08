import json
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

from runtrail.dataset.base import BaseDataset


def _default_field_map(record: dict) -> dict:
    return {"input": record.get("input"), "ground_truth": record.get("ground_truth")}


class BenchmarkAdapter(BaseDataset):
    """Adapts a public benchmark's raw records (GAIA's metadata.jsonl,
    AgentBench's task JSON files, or anything similar) into Runtrail's
    {input, ground_truth} case shape via a caller-supplied field mapping.

    This is a generic JSON/JSONL loader, not a hardcoded client for any one
    benchmark's (possibly gated) hosting — point it at a local export or a
    URL and supply `field_map` for that benchmark's record shape.
    """

    def __init__(
        self,
        name: str,
        records: list[dict[str, Any]],
        *,
        field_map: Callable[[dict], dict] | None = None,
    ):
        self.name = name
        self._records = records
        self._field_map = field_map or _default_field_map

    @classmethod
    def from_jsonl(
        cls, name: str, path: str | Path, *, field_map: Callable[[dict], dict] | None = None
    ) -> "BenchmarkAdapter":
        records = [
            json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()
        ]
        return cls(name, records, field_map=field_map)

    @classmethod
    def from_url(
        cls,
        name: str,
        url: str,
        *,
        field_map: Callable[[dict], dict] | None = None,
        timeout: float = 30.0,
    ) -> "BenchmarkAdapter":
        """Fetch a JSON array or JSONL document of records. Requires the
        'remote' extra: pip install 'runtrail[remote]'.
        """
        try:
            import httpx
        except ImportError as exc:
            raise ImportError(
                "BenchmarkAdapter.from_url requires the 'remote' extra: pip install 'runtrail[remote]'"
            ) from exc

        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        text = response.text

        try:
            parsed = json.loads(text)
            records = parsed if isinstance(parsed, list) else parsed.get("data", [parsed])
        except json.JSONDecodeError:
            records = [json.loads(line) for line in text.splitlines() if line.strip()]

        return cls(name, records, field_map=field_map)

    def __iter__(self) -> Iterator[dict]:
        return iter(self._field_map(record) for record in self._records)

    def __len__(self) -> int:
        return len(self._records)
