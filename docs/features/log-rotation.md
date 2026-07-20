# Feature: Log Splitting and Rotation

## Goal
The Agentic OS currently pipes all output to a monolithic `AgenticOS.log` or stdout. We need to implement distinct log files for the API, Orchestrator, Sandbox, and Database operations. These files must rotate automatically after 3 days and be selectable from the WebUI.

## Specifications
1. **Centralized Logging**: `src/core/logging_config.py` will initialize Python's `TimedRotatingFileHandler`.
2. **Rotation Policy**: Rotate every midnight, keep `backupCount=3`.
3. **Log Files**: 
   - `logs/api.log`
   - `logs/orchestrator.log`
   - `logs/sandbox.log`
   - `logs/database.log`
4. **Docker Persistence**: The `./logs` directory will be mounted as a volume in `docker-compose.yml`.
5. **UI Integration**: The `Logfiles` tab in the WebUI will feature a dropdown to toggle between these 4 log files and stream them via WebSockets.

## Architecture & Security
- The WebSocket endpoint `/api/v1/stream/logs/{log_name}` must strictly validate `log_name` against the allowed list to prevent directory traversal.
