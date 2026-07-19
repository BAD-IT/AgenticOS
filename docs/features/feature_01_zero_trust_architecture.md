# Feature 01: Zero-Trust Architecture & Sandboxing

Agentic OS was built from the ground up to address the fundamental security flaw of autonomous LLM execution: the unrestricted ability to execute arbitrary, hallucinated code on a host machine.

To combat this, the OS employs a strict **Zero-Trust Architecture**.

## 1. The Isolation Boundary
The core brain (the `agenticos_orchestrator`) runs natively with access to the PostgreSQL database and the host filesystem via volume mounts. However, the Orchestrator **never** executes code itself.

Instead, all tool execution and code running happens inside the `agenticos_artifact_runner` Docker container.

## 2. Sandbox Constraints
The `artifact_runner` is heavily constrained at the container level:
- `network_mode: none`: The runner has absolute zero network access. It cannot download external dependencies, phone home, or be used to bridge into the local network.
- `mem_limit: 512m` & `cpus: "0.5"`: The runner is throttled to prevent AI-generated infinite loops (like fork bombs) from crashing the host machine.

## 3. The File-Exchange Contract
Because there is no network, the Orchestrator and the Sandbox must communicate entirely asynchronously via the filesystem:
- **`/workspace/inbox`** (Read-Only): Where the Orchestrator drops files for the Sandbox to process.
- **`/workspace/outbox`** (Read/Write): Where the Sandbox executes code and writes results. The Orchestrator polls this folder to retrieve the outputs of AI tasks.

This architecture ensures that even if the AI turns rogue or hallucinates malicious `rm -rf /` scripts, the damage is strictly contained to the ephemeral Docker sandbox and the output folder.
