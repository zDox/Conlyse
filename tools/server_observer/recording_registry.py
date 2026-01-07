import json
import threading
from pathlib import Path
from typing import Dict
from typing import Optional

from tools.recorder.recorder_logger import get_logger

logger = get_logger()

class RecordingRegistry:
    """Persisted registry of active and finished recordings to allow recovery."""

    def __init__(self, registry_path: Path):
        self.path = Path(registry_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.state: Dict[str, Dict[str, dict]] = {"recording": {}, "completed": {}, "failed": {}}
        self._load()

    def _load(self):
        if not self.path.exists():
            return
        try:
            with self.path.open("r") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    self.state.update({k: v for k, v in data.items() if k in self.state})
        except Exception as exc:
            logger.warning(f"Could not read registry at {self.path}: {exc}")

    def _save(self):
        with self.path.open("w") as f:
            json.dump(self.state, f, indent=2)

    def mark_recording(self, game_id: int, scenario_id: int, replay_path: Optional[str]):
        with self._lock:
            self.state["recording"][str(game_id)] = {
                "scenario_id": scenario_id,
                "replay_path": replay_path,
            }
            self._save()

    def mark_completed(self, game_id: int):
        with self._lock:
            meta = self.state["recording"].pop(str(game_id), None)
            if meta is None:
                meta = {}
            self.state["completed"][str(game_id)] = meta
            self._save()

    def mark_failed(self, game_id: int, reason: str = ""):
        with self._lock:
            meta = self.state["recording"].pop(str(game_id), None)
            if meta is None:
                meta = {}
            meta["reason"] = reason
            self.state["failed"][str(game_id)] = meta
            self._save()

    def is_known(self, game_id: int) -> bool:
        sid = str(game_id)
        return any(sid in bucket for bucket in self.state.values())

    def active(self) -> Dict[int, dict]:
        return {int(k): v for k, v in self.state["recording"].items()}

