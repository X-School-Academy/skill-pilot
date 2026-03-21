# Mock-Up Test

Use this mode only when the user explicitly asks for it.

## When to Use

- The user explicitly says `mock`, `mock up`, `mock-up`, `stub`, `monkeypatch`, or equivalent
- The user explicitly wants isolated unit tests with test doubles
- The user prefers fake inputs or fake dependencies for the task

## Rules

1. Confirm that the user explicitly asked for mock-up testing before introducing mocks or test doubles.
2. Keep the mock-up scope as small as possible.
3. Mock only the dependency boundary needed for isolation.
4. Do not mock the function under test.
5. For Python tests in `core/engine`, write pytest tests in `core/engine/tests`.
6. Name a function test as `test_function_name`.
7. Clearly separate mocked behavior from real project behavior in assertions and printed output.
8. Print raw output when the user needs to inspect runtime details, and make sure the runner shows it.
9. If the task needs output files, place them under `.skillpilot/tests` at the project root.

## Anti-Patterns

- Mocking large portions of the project when a narrower boundary is enough
- Mixing real and fake config without making the boundary obvious
- Using mock-up tests by default when the user did not ask for them
