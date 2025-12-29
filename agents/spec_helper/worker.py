"""
Specification helper agent runtime stub.
"""
from __future__ import annotations

from core.schemas.contracts import AgentType, ResultMessage, TaskMessage, TaskStatus
from core.observability.emitter import emit_runtime_event
from agents.common.base import AgentWorkerBase


class SpecHelperWorker(AgentWorkerBase):
    handled_types = {AgentType.SPECIFICATION_HELPER}
    runtime_name = "agent_spec_helper"

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
            log_output="SpecificationHelper stub: accepted provided interface.",
        )
