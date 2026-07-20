# Feature: Curated Queue UI Grouping

## Goal
Agentic OS utilizes an 11-Queue topology on the backend, which is too granular and cluttered for the default WebUI Left Panel. We will implement "Option B: The Curated Grouping" to abstract these 11 queues into 5 logical pipelines for the user.

## UX Mapping
The Left Panel will display the following grouped pipelines:
1. **📥 Ingestion:** (Maps to `USER_INPUT` + `TASKS`)
2. **⚙️ Processing:** (Maps to `PENDING` + `EMBEDDING` + `IO_WAIT`)
3. **🛡️ Validation:** (Maps to `REVIEW`)
4. **📤 Output:** (Maps to `RESULT_OUTPUT` + `NOTIFICATION`)
5. **⚠️ Errors:** (Maps to `ERROR`) - Displayed only if count > 0, otherwise hidden or styled gracefully.

## Implementation Steps
1. **Frontend HTML:** Update `ui/index.html` left panel queue list to reflect these 5 categories instead of the mock placeholders.
2. **Frontend JS:** Update `ui/app.js` to parse backend queue counts (when available) and aggregate them into these 5 buckets.
3. (Future Backend): Ensure the API emits a dictionary of the 11 queue counts so the frontend can group them.
