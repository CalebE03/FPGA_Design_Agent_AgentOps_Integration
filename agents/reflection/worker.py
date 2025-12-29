"""
Reflection agent runtime. Consumes ReflectionAgent tasks from the agent queue
and returns structured mock insights.
"""
from __future__ import annotations

from core.schemas.contracts import AgentType, ReflectionInsights, ResultMessage, TaskMessage, TaskStatus
from core.observability.emitter import emit_runtime_event
from agents.common.base import AgentWorkerBase


class ReflectionWorker(AgentWorkerBase):
    handled_types = {AgentType.REFLECTION}
    runtime_name = "agent_reflection"

    def handle_task(self, task: TaskMessage) -> ResultMessage:
        insights = ReflectionInsights(
            hypotheses=["Demo passes"],
            likely_failure_points=[],
            recommended_probes=[],
            confidence_score=0.9,
            analysis_notes="No issues observed in mock sim.",
        )
        emit_runtime_event(
            runtime=self.runtime_name,
            event_type="task_completed",
            payload={"task_id": str(task.task_id)},
        )
        return ResultMessage(
            task_id=task.task_id,
            correlation_id=task.correlation_id,
            status=TaskStatus.SUCCESS,
            log_output="Mock reflection complete.",
            reflection_insights=insights,
        )
