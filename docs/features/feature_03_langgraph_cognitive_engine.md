# Feature 03: LangGraph Cognitive Engine

The core reasoning engine of Agentic OS is built natively on `langgraph`. By structuring the AI's "thought process" as a state machine graph, we achieve deterministic control over a highly non-deterministic LLM.

## 1. StateGraph & Pydantic Data Contracts
Every execution passes through the graph utilizing a strictly typed `GraphState` defined via Pydantic v2. This ensures that every node receives exactly the data structure it expects. If the LLM hallucinates an invalid JSON payload, Pydantic immediately rejects it, preventing cascade failures.

## 2. The Constitution Node (Overseer)
We implemented a secondary safety layer known as the Constitution Node (or Review Node). 
If the AI encounters repeated errors (e.g., `tool_error_count >= 3`), the edge routers forcefully divert the execution flow to the Constitution Node. This node intercepts the loop, injects a `<SYSTEM_OVERRIDE>` prompt telling the agent to stop using the failing approach, and forces a pivot in strategy.

## 3. Tool-Scanner Circuit Breakers
To prevent "Tunnel Vision" (where the LLM tries the exact same failing command 100 times in a row), we implemented deterministic hashing.
When the AI proposes a tool call, we generate a SHA-256 hash of the tool name and arguments. If that exact hash exists in the `failed_tool_hashes` state, the Tool-Scanner intercepts the execution *before* hitting the sandbox and instantly returns an error demanding a completely new approach.
