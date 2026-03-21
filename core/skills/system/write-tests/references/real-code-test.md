# Real Code Test

Use this mode by default.

## When to Use

- The user asks for tests without mentioning mock-up or mocks
- The project code can be exercised through its real code path
- The goal is to validate actual project behavior

## Rules

1. Read the target code before writing the test.
2. Use the real module, real function, and real project configuration path.
3. Do not use monkeypatch, mocks, stubs, fake configs, or fabricated data unless the user explicitly asks.
4. For Python tests in `core/engine`, write pytest tests in `core/engine/tests`.
5. Name a function test as `test_function_name`.
6. If the code structure blocks a real test, improve the project code structure first.
7. If import-time validation blocks testing, move it to the correct runtime boundary instead of faking environment state in the test.
8. When testing wrappers such as LLM helpers, assert code behavior such as prompt handoff, raw output visibility, JSON extraction, streaming markers, default parameter behavior, and error handling.
9. Do not assert model intelligence unless the user explicitly wants that.
10. Print raw output when it helps inspect how the real code behaves, and make sure the test runner shows it.
11. If the task needs output files, place them under `.skillpilot/tests` at the project root.

## Anti-Patterns

- Replacing real function calls with mocked return values to bypass project logic
- Writing temporary provider configs when the project already has a real config file
- Inventing fake command outputs for wrapper tests without user approval
- Hiding raw output when the user needs to inspect runtime details
- Writing generated test output files outside `.skillpilot/tests`
