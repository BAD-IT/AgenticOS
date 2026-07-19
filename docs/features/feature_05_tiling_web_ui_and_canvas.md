# Feature 05: Tiling Web UI & Canvas Mode

To interface with the complex backend seamlessly, Agentic OS employs a highly optimized, `dwm`-inspired Tiling Web UI. This interface avoids bloated frameworks, utilizing pure HTML, CSS Flexbox, and JavaScript to deliver an instant, lag-free experience.

## 1. Bidirectional WebSocket Telemetry
Because the OS executes asynchronous tasks in isolated sandboxes, standard HTTP request/response cycles are insufficient. The UI maintains continuous WebSocket connections to `/api/v1/stream/chat` and `/api/v1/stream/notifications`. As the PostgreSQL queues shift, the FastAPI Orchestrator streams real-time telemetry back to the UI, updating the Semantic Terminal and Chat History dynamically.

## 2. Dynamic Flexbox Layout
The layout consists of three resizable glassmorphic panels (Context, CLI, and Terminal). Custom JavaScript event listeners (`mousedown`, `mousemove`) allow the user to grab the invisible splitter margins and drag them to dynamically adjust the viewport widths based on the current context.

## 3. Dynamic Workspaces
Users can manage multiple concurrent workflows by clicking the `+` button to spawn up to 10 isolated workspaces. Navigation is purely native and instant via mouse clicks or `Alt+Num` keyboard shortcuts, swapping the active workspace state flawlessly.

## 4. Canvas Mode
The most unique frontend feature is **Canvas Mode**. When the AI agent successfully programs an interactive HTML/React application, it serves it locally. The user can click `[Toggle Canvas]` to replace the left Context panel with a live `iframe`. This allows the user to directly interact with, preview, and test the software the agent just built without ever leaving the Agentic OS environment.
