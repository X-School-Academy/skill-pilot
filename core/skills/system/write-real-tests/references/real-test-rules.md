# Real Test Rules

Use this checklist when writing or reviewing tests.

## Primary Rules

1. Read the target code before writing the test.
2. Use the real module, real function, and real configuration path.
3. Do not use monkeypatch, mocks, stubs, fake configs, or fabricated data unless the user explicitly asks.
4. Name a function test as `test_function_name`.
5. Prefer one clear test per behavior over long scenario names.
6. If the code structure prevents a real test, improve the code structure first.
7. If the project enforces startup-only validation at import time, move that validation to startup instead of working around it in the test.
8. When testing LLM wrappers, validate the project code behavior:
   - prompt/input handoff
   - raw output visibility
   - JSON extraction
   - streaming markers
   - default parameter behavior
   - error handling
9. Do not assert model intelligence unless the user explicitly wants that.
10. If raw output matters, print it and make sure the test runner shows it.
11. If the task needs output files, place them under `.skillpilot/tests` at the project root.

## Decision Order

1. Can the real code be tested directly as-is?
2. If not, can the production code be improved so it can be tested directly?
3. If not, does the user explicitly permit mocks or fabricated setup?
4. Only after step 3 may a fake or mock-based approach be introduced.

## Anti-Patterns

- Replacing real function calls with mocked return values to bypass project logic
- Writing temporary provider configs when the project already has a real config file
- Inventing fake command outputs for wrapper tests without user approval
- Asserting exact LLM reasoning answers when the code under test is only a transport/parsing wrapper
- Hiding raw output and then guessing why a live test failed
- Writing generated test output files outside `.skillpilot/tests`

## Review Questions

- Does this test exercise the same code path the application uses?
- Does it rely on a fake that the user did not approve?
- Does the test name match the function simply and clearly?
- Is the assertion about code behavior rather than external model quality?
- If the test needed environment setup, is that setup part of the real runtime contract?
