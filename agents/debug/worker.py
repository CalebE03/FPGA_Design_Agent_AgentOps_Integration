"""
Debug agent runtime stub. Returns a placeholder analysis result.
"""
from __future__ import annotations

from core.schemas.contracts import AgentType, ResultMessage, TaskMessage, TaskStatus
from core.observability.emitter import emit_runtime_event
from agents.common.base import AgentWorkerBase


class DebugWorker(AgentWorkerBase):
    handled_types = {AgentType.DEBUG}
    runtime_name = "agent_debug"

    def handle_task(self, task: TaskMessage) -> ResultMessage:
        emit_runtime_event(
            runtime=self.runtime_name,
            event_type="task_completed",
            payload={"task_id": str(task.task_id)},
        )
        return ResultMessage(
            task_id=task.task_id,
            correlation_id=task.correlation_id,
            status=TaskStatus.SUCCESS,
            artifacts_path=None,
            log_output="Debug analysis stub: no failures detected.",
        )
