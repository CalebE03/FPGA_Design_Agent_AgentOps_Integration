"""
Testbench agent runtime. Generates SystemVerilog TBs (LLM-backed when enabled,
fallback stub otherwise).
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import List, Tuple

from core.schemas.contracts import AgentType, ResultMessage, TaskMessage, TaskStatus
from core.observability.emitter import emit_runtime_event
from agents.common.base import AgentWorkerBase
from agents.common.llm_gateway import init_llm_gateway, Message, MessageRole, GenerationConfig


class TestbenchWorker(AgentWorkerBase):
    handled_types = {AgentType.TESTBENCH}
    runtime_name = "agent_testbench"

    def __init__(self, connection_params, stop_event):
        super().__init__(connection_params, stop_event)
        self.gateway = init_llm_gateway()

    def handle_task(self, task: TaskMessage) -> ResultMessage:
        ctx = task.context
        node_id = ctx["node_id"]
        tb_path = Path(ctx.get("tb_path", "")) if ctx.get("tb_path") else Path(ctx["rtl_path"]).with_name(f"{node_id}_tb.sv")
        tb_path.parent.mkdir(parents=True, exist_ok=True)

        if self.gateway and Message:
            tb_source, log_output = asyncio.run(self._llm_generate_tb(ctx, node_id))
        else:
            tb_source, log_output = self._fallback_generate_tb(ctx, node_id)

        tb_path.write_text(tb_source)
        emit_runtime_event(
            runtime=self.runtime_name,
            event_type="task_completed",
            payload={"task_id": str(task.task_id), "artifacts_path": str(tb_path)},
        )
        return ResultMessage(
            task_id=task.task_id,
            correlation_id=task.correlation_id,
            status=TaskStatus.SUCCESS,
            artifacts_path=str(tb_path),
            log_output=log_output,
        )

    async def _llm_generate_tb(self, ctx, node_id: str) -> Tuple[str, str]:
        iface = ctx["interface"]["signals"]
        ports = []
        for sig in iface:
            dir_kw = sig["direction"].lower()
            name = sig["name"]
            width = sig.get("width", 1)
            ports.append(f"{dir_kw} logic [{width-1}:0] {name}" if width > 1 else f"{dir_kw} logic {name}")
        system = (
            "You are a Verification Agent. Generate a simple self-checking SystemVerilog testbench.\n"
            "Use clock/reset if present, drive a few cycles, and assert outputs follow pass-through behavior."
        )
        user = (
            f"Unit Under Test: {node_id}\n"
            f"Ports:\n" + "\n".join(f"- {p}" for p in ports) + "\n"
            "Test basic stimulus to toggle inputs and observe outputs."
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
        return resp.content, f"LLM TB generation via {getattr(resp, 'provider', 'llm')}/{getattr(resp, 'model_name', 'unknown')}"

    def _fallback_generate_tb(self, ctx, node_id: str) -> Tuple[str, str]:
        iface = ctx["interface"]["signals"]
        inputs = [s for s in iface if s["direction"].lower() == "input"]
        outputs = [s for s in iface if s["direction"].lower() == "output"]

        def port_decl(sig):
            width = sig.get("width", 1)
            return f"logic [{width-1}:0] {sig['name']}" if width > 1 else f"logic {sig['name']}"

        port_lines = "\n  ".join(port_decl(s) + ";" for s in iface)
        assigns = "\n  ".join(f"{out['name']} = {inputs[0]['name']};" for out in outputs) if inputs else ""
        tb = f"""`timescale 1ns/1ps

module {node_id}_tb;
  {port_lines}

  {node_id} dut (
    {", ".join(f".{s['name']}({s['name']})" for s in iface)}
  );

  initial begin
    $display("Running stub TB for {node_id}");
    {assigns}
    #10;
    $finish;
  end
endmodule
"""
        return tb, "Fallback TB generation (smoke test)."
