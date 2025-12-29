"""
AgentOps sink placeholder. Wire this sink into EventEmitter when AgentOps is
available; keep semantics out of runtimes.
"""
from __future__ import annotations

from typing import Any

from core.observability.events import Event


class AgentOpsSink:
    def __init__(self) -> None:
        # Extend with AgentOps client initialization when available.
        self.enabled = False

    def send(self, event: Event) -> None:
        if not self.enabled:
            return
        # TODO: integrate with AgentOps SDK; keep as no-op placeholder for now.
        _ = event
