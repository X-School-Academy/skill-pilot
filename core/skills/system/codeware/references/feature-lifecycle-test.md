# Feature Lifecycle: Test

Use when a feature implementation needs validation before merge.

## Steps

1. Read the relevant implementation context (`implementation.md`, `update-impl.md`, or `issues-impl.md`) and `requirements.md`.
2. Use the highest-priority relevant test method:
   - Integration testing: use the web browser agent skill for web pages and browser flows; for Flutter projects, use `flutter test integration_test`.
   - HTTP API testing: use `curl` for HTTP endpoints.
   - WebSocket testing: use `wscat` for WebSocket connections. Install with `pnpm install -g wscat` if not available.
   - Unit testing: write code tests for major complex logic.
3. For each failure found: fix the code, then retest that case.
4. Repeat the test → fix → retest loop until all requirements pass.
5. Only report done when the implementation passes all requirements. Summarize passed checks and any coverage gaps.
