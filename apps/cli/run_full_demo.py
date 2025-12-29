"""
Fuller demo runner:
- Generates design context + DAG via planner_stub
- Launches agent runtimes (implementation/testbench/reflection/debug/spec helper) and deterministic workers (lint/sim/distill)
- Runs orchestrator to drive Implementation -> Lint -> Testbench -> Simulation -> Distill -> Reflection
Requires RabbitMQ running (docker-compose up -d in infrastructure).
EDA steps are mocked so demo runs without tools.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import pika

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.implementation.worker import ImplementationWorker
from agents.testbench.worker import TestbenchWorker
from agents.reflection.worker import ReflectionWorker
from agents.debug.worker import DebugWorker
from agents.spec_helper.worker import SpecHelperWorker
from workers.lint.worker import LintWorker
from workers.sim.worker import SimulationWorker
from workers.distill.worker import DistillWorker
from orchestrator.orchestrator_service import DemoOrchestrator
from orchestrator import planner_stub


def main() -> None:
    planner_stub.generate()

    rabbit_url = os.getenv("RABBITMQ_URL", "amqp://user:password@localhost:5672/")
    try:
        params = pika.URLParameters(rabbit_url)
        conn = pika.BlockingConnection(params)
        conn.close()
    except Exception as exc:  # noqa: BLE001
        print(f"RabbitMQ not reachable at {rabbit_url}. Start docker-compose in infrastructure/. Error: {exc}")
        return

    design_context = REPO_ROOT / "artifacts" / "generated" / "design_context.json"
    dag_path = REPO_ROOT / "artifacts" / "generated" / "dag.json"
    rtl_root = REPO_ROOT / "artifacts" / "generated"
    task_memory_root = REPO_ROOT / "artifacts" / "task_memory"

    stop_event = threading.Event()
    workers = [
        ImplementationWorker(params, stop_event),
        TestbenchWorker(params, stop_event),
        ReflectionWorker(params, stop_event),
        DebugWorker(params, stop_event),
        SpecHelperWorker(params, stop_event),
        LintWorker(params, stop_event),
        DistillWorker(params, stop_event),
        SimulationWorker(params, stop_event),
    ]
    for w in workers:
        w.start()

    try:
        DemoOrchestrator(params, design_context, dag_path, rtl_root, task_memory_root).run()
    finally:
        stop_event.set()
        for w in workers:
            w.join(timeout=1.0)


if __name__ == "__main__":
    main()
