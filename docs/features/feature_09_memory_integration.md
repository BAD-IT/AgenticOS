# Feature 09: Comprehensive Memory Integration

## Goal
To implement the missing memory layers of the Agentic OS: Short-Term (Chat History), Working (LangGraph Checkpointing), and Long-Term (Vector Skills). Without these, the AI remains stateless and cannot maintain context or learn from past tasks.

## Specifications

### 1. Short-Term Memory (Chat History)
- **Problem:** `worker.py` starts every GraphState with `messages=[]`.
- **Solution:** Before calling `app.astream()`, query `system_tasks` for the current `workspace_id`. Convert the past payloads into `HumanMessage` and `AIMessage` objects and inject them into `GraphState.messages`.

### 2. Working Memory (LangGraph Checkpointer)
- **Problem:** LangGraph compiles statelessly (`workflow.compile()`).
- **Solution:** Introduce `AsyncPostgresSaver` from `langgraph-checkpoint-postgres`.
- **Implementation:** 
  - Update `worker.py` and `workflow.py` to utilize the checkpointer.
  - Pass `config={"configurable": {"thread_id": msg_id}}` when calling `astream`.
  
### 3. Long-Term Memory (Experience & Skills)
- **Problem 1 (Bug):** `OLLAMA_API_BASE` points to `localhost` inside Docker, failing to reach Ollama on the host.
- **Problem 2 (Missing RAG):** The Orchestrator does not query the `agent_skills` table.
- **Solution:**
  - Update `.env` to use `http://host.docker.internal:11434` for Ollama.
  - In `node_worker_thinking`, perform a semantic search using `OllamaEmbeddings` on the `agent_skills` table (via `pgvector`).
  - Inject the top matched abstract skill into the `SystemMessage`.
