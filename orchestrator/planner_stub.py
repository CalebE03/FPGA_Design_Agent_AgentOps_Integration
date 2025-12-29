"""
Planner stub that emits a minimal Design Context and DAG from hardcoded
specification fragments. This stands in for the Planner Agent + L1/L2 parsing.

Outputs:
  artifacts/generated/design_context.json
  artifacts/generated/dag.json
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Dict, List, Any

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "artifacts" / "generated"


def _hash_dict(obj: Dict) -> str:
    data = json.dumps(obj, sort_keys=True).encode()
    return hashlib.sha256(data).hexdigest()[:16]


def _counter4_spec() -> Dict[str, Any]:
    return {
        "module": "counter4",
        "interface": {
            "signals": [
                {"name": "clk", "direction": "INPUT", "width": 1},
                {"name": "rst_n", "direction": "INPUT", "width": 1},
                {"name": "en", "direction": "INPUT", "width": 1},
                {"name": "load", "direction": "INPUT", "width": 1},
                {"name": "load_value", "direction": "INPUT", "width": 4},
                {"name": "count", "direction": "OUTPUT", "width": 4},
                {"name": "term", "direction": "OUTPUT", "width": 1},
            ]
        },
        "coverage_goals": {"branch": 0.9, "toggle": 0.85},
        "clocking": {"clk": {"freq_hz": 50e6, "reset": "rst_n", "reset_active_low": True}},
        "demo_behavior": "counter4",
    }


def _generic_spec() -> Dict[str, Any]:
    return {
        "module": "demo_module",
        "interface": {
            "signals": [
                {"name": "clk", "direction": "INPUT", "width": 1},
                {"name": "rst_n", "direction": "INPUT", "width": 1},
                {"name": "in_data", "direction": "INPUT", "width": 8},
                {"name": "out_data", "direction": "OUTPUT", "width": 8},
            ]
        },
        "coverage_goals": {"branch": 0.8, "toggle": 0.7},
        "clocking": {"clk": {"freq_hz": 100e6, "reset": "rst_n", "reset_active_low": True}},
        "demo_behavior": "passthrough",
    }


def generate() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    template = os.getenv("PLANNER_TEMPLATE", "generic").lower()
    if template == "counter4":
        spec = _counter4_spec()
    else:
        spec = _generic_spec()

    design_context = {
        "design_context_hash": None,  # filled after hashing nodes
        "nodes": {
            spec["module"]: {
                "rtl_file": f"rtl/{spec['module']}.sv",
                "testbench_file": f"rtl/{spec['module']}_tb.sv",
                "interface": spec["interface"],
                "uses_library": [],
                "clocking": spec.get("clocking", {}),
                "coverage_goals": spec.get("coverage_goals", {}),
                "demo_behavior": spec.get("demo_behavior", "passthrough"),
            }
        },
        "standard_library": {
            "fifo_sync": {"fingerprint": "lib-fifo-sync-v1"},
            "cdc_sync2": {"fingerprint": "lib-cdc-sync2-v1"},
        },
    }
    design_context["design_context_hash"] = _hash_dict(design_context["nodes"])

    dag = {
        "nodes": [
            {
                "id": spec["module"],
                "type": "module",
                "deps": [],
                "state": "PENDING",
                "artifacts": {},
                "metrics": {},
            },
        ]
    }

    (OUT_DIR / "design_context.json").write_text(json.dumps(design_context, indent=2))
    (OUT_DIR / "dag.json").write_text(json.dumps(dag, indent=2))


if __name__ == "__main__":
    generate()
    print(f"Wrote design context and DAG to {OUT_DIR}")
