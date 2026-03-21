---
name: write-real-tests
description: Write test cases and unit tests against real project code and real project configuration. Use when creating or updating tests and the user wants production-like validation rather than mocks or fake fixtures.
---

# AI Builder - Write Real Tests

Write tests that validate real project behavior instead of testing fabricated stand-ins.

## When to Use This Skill

- The user asks to create or update tests
- A function or module should be tested against the real project code path
- Existing tests rely too much on mocks, fake config, or invented data
- A test should reflect actual runtime behavior as closely as possible

## Your Roles in This Skill

- **QA Engineer**: Define what behavior must be validated and how to observe it safely
- **Backend Developer**: Trace the real code path, remove unnecessary indirection, and wire tests to actual project behavior
- **Technical Writer**: Keep the test intent, naming, and output readable

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Inspect the real code path first

- Read the target function and all direct callers that define its real behavior
- Check whether the behavior depends on project configuration, environment loading, startup flow, or external processes
- Identify whether the test should exercise a helper, a module boundary, or a higher-level integration path

### Step 2: Default to real project behavior

- Test the real function from the real module
- Use the real project configuration files, real default values, and real code paths whenever the project already defines them
- Prefer the real dependency wiring already present in the repo over ad hoc test setup
- If runtime validation currently happens at import time and blocks testability, fix the project code so validation happens at the correct runtime boundary instead of faking the environment in the test

### Step 3: Do not use mocks or fake stand-ins unless the user explicitly asks

- Do not use monkeypatching, mocking, stub executables, temporary fake provider configs, or invented test-only replacement data unless the user explicitly requests that style
- Do not create fake config files when the project already has a real config source
- Do not replace real function calls with mocked return values just to make the test pass
- If a real dependency makes testing difficult, first try to improve the project code so the real path can be exercised safely
- If true isolation is unavoidable, stop and ask the user before introducing mocks or fabricated data

### Step 4: Keep test names simple and direct

- Name a test for a function as `test_function_name`
- Only add a suffix when there are multiple distinct behaviors that truly need separate tests
- Avoid verbose names that repeat the full scenario in prose if the assertions already make the intent clear

### Step 5: Assert code behavior, not model intelligence

- When testing an LLM-facing function, test the wrapper code behavior such as prompt handoff, raw output visibility, JSON extraction, stream completion, or error handling
- Do not hard-code assertions around whether the model solved the task correctly unless the user explicitly wants a live semantic expectation
- If the user wants to inspect live outputs, print or otherwise surface the raw output in the test so failures are diagnosable

### Step 6: Use real defaults when the code supports them

- If a function accepts `provider_id=None` or similar default-driven behavior, test that path directly instead of manually overriding the provider
- If a function does not support default-driven behavior but should, update the implementation first so the test can cover the real default path
- Keep the test aligned with public function signatures, not with internal shortcuts

### Step 7: Keep the environment honest

- If a test reveals import-time side effects that should only happen at startup, move that logic into the proper runtime entry point
- Avoid using test-only environment hacks when the better fix is to correct module initialization behavior
- Only seed environment variables in tests when that environment is genuinely part of the runtime contract and the user accepts that setup

### Step 8: Verify and report clearly

- Run the relevant test file or test target after editing
- If the test output should be visible, ensure the chosen test runner invocation does not hide stdout
- If the task needs output files, write them under `.skillpilot/tests` at the project root
- Report what was verified and what still depends on live external systems

## Expected Output

- A test file or updated test file that exercises the real project code path
- Minimal setup, minimal indirection, and no hidden fake behavior
- Readable test names such as `test_function_name`
- Raw output surfaced when it materially helps debugging
- Any generated test output files stored under `.skillpilot/tests`

## Key Principles

- Real code path first
- Real config first
- No mocks unless explicitly requested
- Fix project structure before faking project behavior
- Test wrapper logic separately from model intelligence

## Common Issues

- Import-time exits in modules:
  move validation to startup or another runtime boundary instead of faking env in tests
- Hidden stdout in pytest:
  use a runner mode that shows raw output when the user wants to inspect it
- Output file placement:
  write generated test outputs under `.skillpilot/tests` instead of scattering them elsewhere in the repo
- Over-asserting LLM correctness:
  assert wrapper behavior and data shape unless the user explicitly wants semantic validation
- Fake config drift:
  use the real repo config instead of temporary test-only config files

## References

- For the detailed rule set and checklist, refer to `references/real-test-rules.md`
