# Feature Lifecycle: Test

Use when a feature implementation needs validation before merge.

## Steps

1. Read the referenced implementation context.
2. Use the highest-priority relevant test method:
   - Integration testing: use the web browser agent skill for web pages and browser flows; for Flutter projects, use `flutter test integration_test`.
   - HTTP API testing: use `curl` for HTTP endpoints.
   - WebSocket testing: use `wscat` for WebSocket connections. Install with `pnpm install -g wscat` if not available.
   - Unit testing: write code tests for major complex logic.
3. Summarize passed checks, failed checks, bugs found, and coverage gaps.
