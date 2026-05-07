# Stage Reference: test

Test a Vibe Coding project implementation and report the results.

## When to Use

- The user asks to test the implementation
- `design-docs/implement.md` exists
- Goal is validation, bug discovery, or coverage analysis

## Steps

### Step 1: Read the Implementation Context

Read `design-docs/implement.md` and identify the affected flows.

### Step 2: Run Relevant Checks

Use this priority order — apply higher-priority methods first and cover as much code as possible:

1. **Integration testing** (highest priority): use the `agent-browser` skill for end-to-end validation of web pages, interactive flows, or any browser-accessible interfaces. For Flutter projects, use `flutter test integration_test`.
2. **HTTP API testing**: use `curl` for HTTP API endpoints.
3. **WebSocket testing**: use `wscat` for WebSocket connections (`pnpm install -g wscat` if missing).
4. **Unit testing**: write code tests for major complex logic functions.

Apply only the methods relevant to the project.

### Step 3: Save the Test Report

Write results to `design-docs/tested.md` (created fresh per test pass): passed checks, failed checks, bugs found, coverage gaps.

### Step 4: Hand off

Once the user has decided what to do with the results (typically by writing `issues.md` or `update.md`), the consuming stage archives `tested.md`:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/tested.md "design-docs/archive/tested.$timestamp.md"
```

If the next stage runs in the same turn, archive at that point. Otherwise leave `tested.md` in place for human review.
