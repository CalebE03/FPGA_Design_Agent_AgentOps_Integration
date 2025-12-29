"""
Distillation worker for demo: consumes process_tasks (using DISTILLATION WorkerType)
and produces a distilled artifact record (mocked).
"""
from __future__ import annotations

import threading
from pathlib import Path

import pika
from core.schemas.contracts import DistilledDataset, ResultMessage, TaskMessage, TaskStatus
from core.observability.emitter import emit_runtime_event

TASK_EXCHANGE = "tasks_exchange"
RESULTS_ROUTING_KEY = "RESULTS"


class DistillWorker(threading.Thread):
    def __init__(self, connection_params: pika.ConnectionParameters, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.connection_params = connection_params
        self.stop_event = stop_event

    def run(self) -> None:
        with pika.BlockingConnection(self.connection_params) as conn:
            ch = conn.channel()
            ch.basic_qos(prefetch_count=1)
            for method, props, body in ch.consume("process_tasks", inactivity_timeout=0.5):
                if self.stop_event.is_set():
                    break
                if body is None:
                    continue
                task = TaskMessage.model_validate_json(body)
                # Only handle distillation tasks (skip others)
                if task.task_type.value != "DistillationWorker":
                    ch.basic_nack(method.delivery_tag, requeue=True)
                    continue
                result = self.handle_task(task)
                self._publish_result(ch, result)
                ch.basic_ack(method.delivery_tag)

    def handle_task(self, task: TaskMessage) -> ResultMessage:
        dummy_dataset = DistilledDataset(
            original_data_size=1024,
            distilled_data_size=128,
            compression_ratio=8.0,
            failure_focus_areas=["demo_signal"],
            data_path=str(Path(task.context["rtl_path"]).with_suffix(".distill.json")),
        )
        emit_runtime_event(
            runtime="worker_distill",
            event_type="task_completed",
            payload={"task_id": str(task.task_id), "dataset": dummy_dataset.data_path},
        )
        return ResultMessage(
            task_id=task.task_id,
            correlation_id=task.correlation_id,
            status=TaskStatus.SUCCESS,
            log_output="Mock distillation complete.",
            distilled_dataset=dummy_dataset,
        )

    def _publish_result(self, ch: pika.adapters.blocking_connection.BlockingChannel, result: ResultMessage) -> None:
        ch.basic_publish(
            exchange=TASK_EXCHANGE,
            routing_key=RESULTS_ROUTING_KEY,
            body=result.model_dump_json().encode(),
            properties=pika.BasicProperties(content_type="application/json"),
        )
