# Feature 22: Canvas Mode (Artifact Rendering)

## Implementation
- Left panel gets a "Canvas" toggle button in the header.
- Clicking toggles between Live Cognitive Trace and an iframe-based Canvas view.
- `loadCanvas(htmlContent)` writes HTML into a sandboxed iframe.
- Auto-switches to Canvas mode when an artifact is loaded.

## Security
- Iframe uses `sandbox="allow-scripts allow-same-origin"` for isolation.
- Content is rendered locally, not fetched from external URLs.

## Future
- Agent can output HTML artifacts (charts, tables, previews) directly to Canvas.
- File explorer can preview HTML files from outbox in Canvas.
