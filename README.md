# Agentic OS

**Agentic OS** is an autonomous, LangGraph-driven, Zero-Trust operating system running locally via OrbStack. It is designed to safely execute complex AI workflows by isolating the Orchestrator from the Artifact Runner environment, utilizing a robust PostgreSQL-backed queue topology and a beautiful `dwm`-style Tiling Web UI.

## 🧠 What makes this an "Agentic OS" and not just an Agent Harness?

Most AI agents (like AutoGPT or standard LangChain wrappers) are **"harnesses"**: monolithic scripts running in a single process, executing code in their own vulnerable environment, and relying on in-memory loops. 

We are building a true **Agentic Operating System**, defined by core OS principles:
1. **The Kernel (State Machine)**: Instead of arbitrary prompt loops, our control flow is a deterministic, LangGraph-driven state machine enforcing strict Pydantic data contracts.
2. **The Scheduler (Background Worker)**: The API does not block to run AI tasks. It pushes to a PostgreSQL queue. A decoupled background worker daemon continuously polls and processes tasks asynchronously, with per-tool timeout isolation.
3. **Memory Management (PostgreSQL)**: The entire system state, cognitive traces, and queues are persisted in a robust database, allowing for system reboots without memory loss. `pgvector` skills are generated only for meaningful multi-step tasks.
4. **Sandboxing (Zero-Trust)**: The orchestrator never executes untrusted code. Code is executed in an isolated, network-less `artifact_runner` Docker container. Data moves strictly through `/workspace/inbox` and `/workspace/outbox`.
5. **Observability (System Monitor)**: Structured JSON logging with task ID correlation across all containers. Real-time WebSockets stream the "Cognitive Trace", and a modern collapsible Thinking Block shows the LLM's reasoning process in the chat UI.

---

## 🚀 Key Features

*   **Zero-Trust Architecture**: Sandboxed executions. The `artifact_runner` Docker container has absolutely no network access and strict CPU/Memory limits. File exchange occurs strictly through `/workspace/inbox` and `/workspace/outbox`.
*   **LangGraph Engine**: Deeply orchestrated cognitive workflows built natively on `langgraph`, enforcing strict Pydantic v2 data contracts. Async tool execution with per-tool timeout isolation.
*   **SRE & Experience Consolidation**: Natively triages fatal errors, triggers idle garbage collection, and generates `pgvector` Skill abstractions — only for meaningful multi-step tasks.
*   **Tiling Web UI**: A highly responsive interface featuring Dynamic Workspaces, a live **Cognitive Trace** feed, and a modern collapsible **Thinking Block** that shows the LLM's reasoning process in real-time.
*   **Production Hardening**: Health check endpoints, container restart policies, structured JSON logging with task ID correlation, and `PYTHONUNBUFFERED` for reliable log visibility.

---

## 🛠 Prerequisites

1.  **OrbStack** (or Docker Desktop) installed locally.
2.  **uv** (Astral) installed for python dependency management.
3.  **Local Ollama Server** running on `localhost:11434` with `gemma4:12b` pulled (`ollama run gemma4:12b`).
4.  **GitHub CLI** (`gh`) logged in, as this repository enforces Feature-Driven Development via GitHub PRs.

---

## ⚙️ Setup & Installation

### 1. Environment Variables
Create a `.env` file in the root directory:
```env
LLM_MODEL=gemma4:12b
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/agenticos
OLLAMA_API_BASE=http://localhost:11434
```

### 2. Boot the Agentic OS
Start the Database, the Orchestrator API, and the isolated Artifact Runner via Docker Compose:
```bash
docker compose up -d --build
```
This automatically boots PostgreSQL with `pgvector`, mounts the 11-Queue Tables via `init.sql`, and exposes the Orchestrator on port 8000.

### 3. Open the UI
Navigate to the interactive desktop environment:
```text
http://localhost:8000/ui/index.html
```

---

## ⌨️ Web UI Usage Guide

*   **Workspaces**: Click the `+` button in the top bar to dynamically spawn new workspaces. Switch between them instantly by clicking their numbers or pressing `Alt+1` through `Alt+0`.
*   **Resizers**: Click and drag the glowing borders between panels to adjust your layout width.
*   **Quick Commands**: Type `/time`, `/clear`, `/session`, or `/stats` in the CLI input. Local JavaScript will instantly intercept these to provide system telemetry without querying the LLM backend.

*   **Greeting System**: Simply say `hi`, `hello`, or `sup` to see the native UI response. 

---

## 🧪 Testing the Ecosystem

We utilize a comprehensive Playwright and Pytest automation suite to guarantee system integrity.

1. Install Dev dependencies (including Playwright):
```bash
uv pip install -r requirements-dev.txt
playwright install chromium
```
2. Run the End-to-End Suite:
```bash
pytest tests/ -v
```
This autonomously verifies the `asyncpg` queue connections, HTTP boundaries, Playwright UI functionality, and local `litellm` connectivity to Ollama.
