import json
import threading
from pathlib import Path
from typing import Any


class Checkpoint:
    """Persists per-case results keyed by case_id, so an interrupted Harness.run()
    can resume from where it left off instead of re-running completed cases.
    """

    def __init__(self, run_id: str, checkpoint_dir: str | Path = ".runtrail_checkpoints"):
        self.run_id = run_id
        self.path = Path(checkpoint_dir) / f"{run_id}.json"
        self._lock = threading.Lock()

    def save_case(self, case_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            data = self._read()
            data[case_id] = result
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data))

    def completed_case_ids(self) -> list[str]:
        return list(self._read().keys())

    def load(self) -> dict[str, dict[str, Any]]:
        return self._read()

    def clear(self) -> None:
        self.path.unlink(missing_ok=True)

    def _read(self) -> dict[str, dict[str, Any]]:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())
