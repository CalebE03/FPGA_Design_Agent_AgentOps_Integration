"""
FastAPI bridge to expose the demo orchestrator state over HTTP for the VS Code extension.
Endpoints:
- POST /run : start a demo run (planner + orchestrator + workers)
- GET /state : returns node states and log tails
- GET /logs/{node_id} : returns concatenated logs for a node

This server runs workers in background threads and spawns an orchestrator per run.
"""
from __future__ import annotations

import asyncio
import os
import sys
import threading
from pathlib import Path
from typing import Dict, List

import shutil
import pika
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from orchestrator import planner_stub
from orchestrator.orchestrator_service import DemoOrchestrator
from agents.implementation.worker import ImplementationWorker
from agents.testbench.worker import TestbenchWorker
from agents.reflection.worker import ReflectionWorker
from agents.debug.worker import DebugWorker
from agents.spec_helper.worker import SpecHelperWorker
from workers.lint.worker import LintWorker
from workers.sim.worker import SimulationWorker
from workers.distill.worker import DistillWorker
from agents.common.llm_gateway import init_llm_gateway, Message, MessageRole, GenerationConfig

ARTIFACTS = REPO_ROOT / "artifacts" / "generated"
TASK_MEMORY = REPO_ROOT / "artifacts" / "task_memory"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

state_lock = threading.Lock()
node_state: Dict[str, Dict] = {}
workers_started = False
stop_event = threading.Event()
chat_history: List[Dict[str, str]] = []
spec_helper_gateway = None


def init_spec_helper_gateway():
    """Initialize shared LLM gateway for the spec helper chat."""
    global spec_helper_gateway
    spec_helper_gateway = init_llm_gateway()
    return spec_helper_gateway


def state_callback(node_id: str, new_state: str) -> None:
    with state_lock:
        if node_id not in node_state:
            node_state[node_id] = {"id": node_id}
        node_state[node_id]["state"] = new_state
        node_state[node_id]["logTail"] = tail_logs(node_id)

def reset_state():
    with state_lock:
        node_state.clear()
    # clear task memory for fresh demo run
    if TASK_MEMORY.exists():
        shutil.rmtree(TASK_MEMORY)
    TASK_MEMORY.mkdir(parents=True, exist_ok=True)
    chat_history.clear()


def tail_logs(node_id: str) -> str:
    logs: List[str] = []
    node_dir = TASK_MEMORY / node_id
    if not node_dir.exists():
        return ""
    for stage in sorted(node_dir.iterdir()):
        log_file = stage / "log.txt"
        if log_file.exists():
            logs.append(f"[{stage.name}] {log_file.read_text().strip()}")
    return "\n".join(logs[-3:]) if logs else ""


def start_workers(params: pika.ConnectionParameters) -> List[threading.Thread]:
    global workers_started
    if workers_started:
        return []
    workers_started = True
    threads = [
        ImplementationWorker(params, stop_event),
        TestbenchWorker(params, stop_event),
        ReflectionWorker(params, stop_event),
        DebugWorker(params, stop_event),
        SpecHelperWorker(params, stop_event),
        LintWorker(params, stop_event),
        DistillWorker(params, stop_event),
        SimulationWorker(params, stop_event),
    ]
    for t in threads:
        t.start()
    return threads


@app.post("/run")
def run_demo():
    rabbit_url = os.getenv("RABBITMQ_URL", "amqp://user:password@localhost:5672/")
    try:
        params = pika.URLParameters(rabbit_url)
        conn = pika.BlockingConnection(params)
        conn.close()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"RabbitMQ not reachable: {exc}")

    reset_state()
    init_spec_helper_gateway()
    planner_stub.generate()
    threads = start_workers(params)
    orch = DemoOrchestrator(
        params,
        ARTIFACTS / "design_context.json",
        ARTIFACTS / "dag.json",
        ARTIFACTS,
        TASK_MEMORY,
        state_callback=state_callback,
    )
    t = threading.Thread(target=orch.run, daemon=True)
    t.start()
    return {"status": "started"}


@app.post("/reset")
def reset_demo_state():
    """
    Clears in-memory node state, chat history, and artifacts/task_memory artifacts.
    Does not stop running workers; use before starting a new demo run.
    """
    reset_state()
    return {"status": "reset"}


@app.get("/state")
def get_state():
    with state_lock:
        nodes = list(node_state.values())
    return {"nodes": nodes}


@app.get("/logs/{node_id}")
def get_logs(node_id: str):
    node_dir = TASK_MEMORY / node_id
    if not node_dir.exists():
        raise HTTPException(status_code=404, detail="node not found")
    logs: List[str] = []
    for stage in sorted(node_dir.iterdir()):
        log_file = stage / "log.txt"
        if log_file.exists():
            logs.append(f"[{stage.name}]\n{log_file.read_text()}")
    return {"node": node_id, "logs": "\n\n".join(logs)}


@app.get("/chat")
def get_chat_history():
    return {"history": chat_history}


@app.post("/chat")
async def send_chat(message: Dict[str, str]):
    user_msg = message.get("message", "").strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="empty message")

    chat_history.append({"role": "user", "content": user_msg})
    init_spec_helper_gateway()
    reply = await generate_spec_helper_reply(user_msg)
    chat_history.append({"role": "agent", "content": reply})
    return {"reply": reply, "history": chat_history}


@app.post("/chat/reset")
def reset_chat():
    chat_history.clear()
    return {"history": chat_history}


async def generate_spec_helper_reply(user_msg: str) -> str:
    """
    LLM-backed spec helper; falls back to lightweight L1-L5 parsing when LLM disabled/unavailable.
    """
    if os.getenv("USE_LLM") == "1" and spec_helper_gateway and Message and MessageRole and GenerationConfig:
        try:
            system = (
                "You are the Specification Helper Agent for RTL designs. "
                "You extract and refine L1-L5: intent, interface, verification goals/coverage, architecture/clocking, acceptance. "
                "Return a short structured summary and 2-3 clarifying questions if needed. "
                "Be concise; prefer bullet lists."
            )
            msgs: List[Message] = [Message(role=MessageRole.SYSTEM, content=system)]
            for m in chat_history[-6:]:
                role = m.get("role", "user")
                if role == "agent":
                    msgs.append(Message(role=MessageRole.ASSISTANT, content=m["content"]))
                else:
                    msgs.append(Message(role=MessageRole.USER, content=m["content"]))
            msgs.append(Message(role=MessageRole.USER, content=user_msg))
            cfg = GenerationConfig(temperature=0.2, max_tokens=500)
            resp = await spec_helper_gateway.generate(messages=msgs, config=cfg)  # type: ignore
            return resp.content
        except Exception:
            # fall through to mock parse
            pass

    # Fallback: lightly parse user text for L1-L5 hints and echo back.
    sections = _parse_l1_l5(user_msg)
    if sections:
        lines = ["Spec Helper (mock): captured your spec summary:"]
        for key in ["L1", "L2", "L3", "L4", "L5"]:
            if key in sections:
                lines.append(f"- {key}: {sections[key]}")
        lines.append("If this looks right, kick off /run. For richer iteration, set USE_LLM=1 and provide OPENAI_API_KEY.")
        return "\n".join(lines)
    return (
        "Spec Helper (mock): Thanks for the details. I couldn't parse L1–L5 sections.\n"
        "Please include labeled bullets for L1 intent, L2 interface, L3 verification/coverage, L4 architecture/clocking, L5 acceptance criteria.\n"
        "Or set USE_LLM=1 with an API key for full parsing."
    )


def _parse_l1_l5(text: str) -> Dict[str, str]:
    sections: Dict[str, str] = {}
    for line in text.splitlines():
        clean = line.strip().lstrip("-").strip()
        lower = clean.lower()
        for key in ["l1", "l2", "l3", "l4", "l5"]:
            if lower.startswith(key):
                parts = clean.split(":", 1)
                val = parts[1].strip() if len(parts) > 1 else clean[len(key) :].strip()
                label = key.upper()
                if val:
                    sections[label] = val
    return sections
