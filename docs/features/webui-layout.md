# Feature: WebUI Layout & Command Center

## Goal
Transform the Agentic OS WebUI into a professional-grade command center by utilizing the empty left and right panels, and introducing dedicated tabs for database and logfile monitoring.

## 1. Left Panel (System State)
- **Problem**: Currently displays static text ("System Context Loaded").
- **Solution**: Replace with live system queues, workspace metadata, and system health (Memory/DB status).

## 2. Right Panel (Workspace Explorer)
- **Problem**: Currently an empty placeholder ("PREVIEW & ARTIFACTS").
- **Solution**: Implement a file tree for `/workspace/inbox` and `/workspace/outbox`, along with a Markdown/JSON preview for artifacts and agent states.

## 3. Database Tab
- **Problem**: No visibility into the internal `pgvector` or queue tables.
- **Solution**: A new tab in the center panel to run read-only queries or browse tables with a search bar and dropdown selector.

## 4. Logfiles Tab
- **Problem**: Debugging requires dropping to the terminal.
- **Solution**: A new tab streaming backend logs (`uvicorn`, `agenticos`) via WebSockets with filtering and auto-scroll.

## Architecture
- **Frontend**: Update `index.html` and `app.js` with new components and WebSocket listeners.
- **Backend**: Add new `/api/v1/stream/logs` endpoint to tail log files. Add `/api/v1/db/query` endpoint for the DB tab.
