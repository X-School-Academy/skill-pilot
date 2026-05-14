# Stage Reference: test

Test a Vibe Coding project implementation and report the results.

## When to Use

- The user asks to test the implementation
- `design-docs/implementation.md` exists
- Goal is validation, bug discovery, or coverage analysis

## Steps

### Step 1: Read the Implementation Context

Read `design-docs/implementation.md` and identify the affected flows.

### Step 2: Run Relevant Checks

Use this priority order — apply higher-priority methods first and cover as much code as possible:

1. **Integration testing** (highest priority): use the `agent-browser` skill for end-to-end validation of web pages, interactive flows, or any browser-accessible interfaces. For Flutter projects, use `flutter test integration_test`.
2. **HTTP API testing**: use `curl` for HTTP API endpoints.
3. **WebSocket testing**: use `wscat` for WebSocket connections (`pnpm install -g wscat` if missing).
4. **Unit testing**: write code tests for major complex logic functions.

Apply only the methods relevant to the project.

### Step 3: Fix Failures and Retest

If any checks fail, fix the code immediately and rerun the relevant checks. Repeat until all requirements pass. Do not proceed to the next stage while failures remain.

### Step 4: Save the Test Report

Write results to `design-docs/tested.md` (created fresh per test pass): passed checks, fixed issues, remaining risks, coverage gaps.

Update `design-docs/implementation.md` if the fixes changed what was implemented.

### Step 5: Hand off

Once the user has decided what to do with the results (or when running in the default new-project flow, proceed directly to `review`), the consuming stage archives `tested.md`:

```bash
timestamp=$(date +"%Y-%m-%d-%H%M")
mv design-docs/tested.md "design-docs/archive/tested.$timestamp.md"
```

If the next stage runs in the same turn, archive at that point. Otherwise leave `tested.md` in place for human review.
