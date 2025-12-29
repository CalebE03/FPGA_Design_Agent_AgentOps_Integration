"""
Implementation agent runtime. Generates RTL (LLM-backed when enabled, otherwise
fallback stub) and writes artifacts to the provided path.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Tuple

from core.schemas.contracts import AgentType, ResultMessage, TaskMessage, TaskStatus
from core.observability.emitter import emit_runtime_event
from agents.common.base import AgentWorkerBase
from agents.common.llm_gateway import init_llm_gateway, Message, MessageRole, GenerationConfig


class ImplementationWorker(AgentWorkerBase):
    handled_types = {AgentType.IMPLEMENTATION}
    runtime_name = "agent_implementation"

    def __init__(self, connection_params, stop_event):
        super().__init__(connection_params, stop_event)
        self.gateway = init_llm_gateway()

    def handle_task(self, task: TaskMessage) -> ResultMessage:
        ctx = task.context
        node_id = ctx["node_id"]
        rtl_path = Path(ctx["rtl_path"])
        rtl_path.parent.mkdir(parents=True, exist_ok=True)

        if self.gateway and Message:
            rtl_source, log_output = asyncio.run(self._llm_generate_impl(ctx, node_id))
        else:
            rtl_source, log_output = self._fallback_generate_impl(ctx, node_id)

        rtl_path.write_text(rtl_source)
        emit_runtime_event(
            runtime=self.runtime_name,
            event_type="task_completed",
            payload={"task_id": str(task.task_id), "artifacts_path": str(rtl_path)},
        )
        return ResultMessage(
            task_id=task.task_id,
            correlation_id=task.correlation_id,
            status=TaskStatus.SUCCESS,
            artifacts_path=str(rtl_path),
            log_output=log_output,
        )

    async def _llm_generate_impl(self, ctx, node_id: str) -> Tuple[str, str]:
        iface = ctx["interface"]["signals"]
        port_lines = []
        for sig in iface:
            dir_kw = sig["direction"].lower()
            name = sig["name"]
            width = sig.get("width", 1)
            port_lines.append(f"{dir_kw} logic [{width-1}:0] {name}" if width > 1 else f"{dir_kw} logic {name}")
        system = (
            "You are an RTL Implementation Agent. Generate synthesizable SystemVerilog.\n"
            "Rules: use always_ff for sequential logic, always_comb for combinational, no latches, reset async active-low if rst_n exists, no delays.\n"
            "Output ONLY code, no prose."
        )
        user = (
            f"Module name: {node_id}\n"
            f"Ports:\n" + "\n".join(f"- {p}" for p in port_lines) + "\n"
            "Implement a simple passthrough/placeholder consistent with interface."
        )
        msgs: List[Message] = [
            Message(role=MessageRole.SYSTEM, content=system),
            Message(role=MessageRole.USER, content=user),
        ]
        cfg = GenerationConfig(
            temperature=0.2,
            max_tokens=600,
        )
        resp = await self.gateway.generate(messages=msgs, config=cfg)  # type: ignore[arg-type]
        return resp.content, f"LLM generation via {getattr(resp, 'provider', 'llm')}/{getattr(resp, 'model_name', 'unknown')}"

    def _fallback_generate_impl(self, ctx, node_id: str) -> Tuple[str, str]:
        iface = ctx["interface"]["signals"]
        ports = []
        assigns = []
        for sig in iface:
            dir_kw = sig["direction"].lower()
            name = sig["name"]
            width = sig.get("width", 1)
            ports.append(f"{dir_kw} logic [{width-1}:0] {name}" if width > 1 else f"{dir_kw} logic {name}")
            if dir_kw == "output":
                src = next((s for s in iface if s["direction"].lower() == "input"), None)
                if src:
                    assigns.append(f"  assign {name} = {src['name']};")
        port_block = ",\n    ".join(ports)
        assign_block = "\n".join(assigns) if assigns else "  // passthrough stub"
        rtl = f"""module {node_id} (
    {port_block}
);

{assign_block}

endmodule
"""
        return rtl, "Fallback RTL generation (passthrough stub)."
