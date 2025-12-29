# Multi-Agent Hardware Design System

LLM-driven agents + deterministic workers that take frozen hardware intent to verified RTL/testbenches through a queued, state-machine-controlled flow. Planning (L1–L5) is frozen first; execution then runs mechanically.

## Runtime Layout

- `apps/cli/` — CLI utilities (validation, reports)  
- `core/schemas/` — shared message contracts; `core/observability/` defines structured events  
- `agents/` — per-role agent runtimes (implementation, testbench, debug, reflection, spec helper)  
- `adapters/llm/` — LLM provider integrations; `adapters/observability/agentops.py` sink placeholder  
- `tests/core/schemas/`, `tests/infrastructure/` — contract and infrastructure suites  
- `docs/` — architecture/process docs  

## Quick Start

### Broker (RabbitMQ)

```bash
cd infrastructure
docker-compose up -d        # start broker
docker-compose ps           # verify
# docker-compose down       # stop
```

- UI: http://localhost:15672 (user/password)  
- AMQP: amqp://user:password@localhost:5672/  
- Queues: `agent_tasks`, `process_tasks`, `simulation_tasks`, `dead_letter_queue`

### LLM configuration

- Set `USE_LLM=1`.  
- OpenAI: `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, optional `OPENAI_MODEL` (defaults gpt-4.1-mini).  
- Groq: `LLM_PROVIDER=groq`, `GROQ_API_KEY`, optional `GROQ_MODEL` (e.g., `llama-3.1-8b-instant`).  
- Spec Helper chat uses the same gateway; falls back to mock parsing when unset.

## Tests

- Contracts: `pytest tests/core/schemas -q`  
- Infrastructure: `python run_infrastructure_tests.py` or `pytest tests/infrastructure -v`  

## Documentation

- `docs/overview.md` — planning/execution tour  
- `docs/architecture.md` — runtime topology and queues  
- `docs/agents.md` — agent roles  
- `docs/spec-and-planning.md` — L1–L5 checklist; artifacts under `artifacts/task_memory/specs/`  
- `docs/queues-and-workers.md` — broker/DLQ details  
- `docs/schemas.md` + `core/schemas/SCHEMAS.md` — message contracts  
