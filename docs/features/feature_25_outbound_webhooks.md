# Feature 25: Outbound Webhooks

## Implementation
- `webhook_url` column added to `system_tasks` table.
- `POST /api/v1/tasks/submit` accepts optional `webhook_url` query param.
- After task completes (RESULT_OUTPUT or ERROR), worker fires `_fire_webhook()`.
- Sends POST with JSON body: `{message_id, payload, status}`.
- Fire-and-forget via `asyncio.create_task()` — doesn't block the worker.
- 10-second timeout on webhook delivery.

## Use Cases
- Notify external systems (Slack, Discord, CI/CD) when a task finishes.
- Chain with external automation platforms.
- Integrate with monitoring/alerting systems.
