"""
Task Memory utilities for the demo. Persists logs and artifacts paths to a
filesystem layout under artifacts/task_memory/{node}/{stage}/.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


class TaskMemory:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def record_log(self, node_id: str, stage: str, content: str) -> Path:
        path = self.root / node_id / stage / "log.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def record_artifact_path(self, node_id: str, stage: str, artifact_path: str) -> Path:
        path = self.root / node_id / stage / "artifact_path.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(artifact_path)
        return path
