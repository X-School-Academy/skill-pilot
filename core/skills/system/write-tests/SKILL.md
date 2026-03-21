---
name: write-tests
description: Write tests for project code using either real code tests or mock-up tests. Use when creating or updating tests, default to real code tests unless the user explicitly asks for mock-up tests.
---

# AI Builder - Write Tests

Write tests for project code using the correct test style for the task.

## When to Use This Skill

- The user asks to create or update tests
- A function, module, or feature should be validated
- The user wants a unit test or integration-style code test
- Existing tests should be rewritten to match project testing rules

## Your Roles in This Skill

- **QA Engineer**: Define what behavior should be validated and choose the right test type
- **Backend Developer**: Trace the actual code path and implement the test cleanly
- **Technical Writer**: Keep test names, output, and assertions readable

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Choose the test type

- If the user explicitly says `mock`, `mock up`, `mock-up`, `monkeypatch`, `stub`, or otherwise asks for fake/test-double-based testing, use **mock-up test**
- If the user does not explicitly ask for mock-up testing, default to **real code test**
- If the correct test type is unclear, choose **real code test**

### Step 2: For Python code, place tests in the standard location

- For Python code under `core/engine`, write pytest tests under `core/engine/tests`
- Use `pytest` for Python tests
- Name a function test as `test_function_name`

### Step 3: Follow the matching reference

- For **real code test**, refer to `references/real-code-test.md`
- For **mock-up test**, refer to `references/mock-up-test.md`

### Step 4: Verify and report clearly

- Run the relevant test target after editing
- Print raw output in the test when the function or flow returns useful runtime details
- Ensure the chosen test runner invocation does not hide stdout when raw output should be inspected
- If the task needs output files, write them under `.skillpilot/tests` at the project root
- Report what was verified and what still depends on live external systems

## Expected Output

- A new or updated test file using the correct test style
- Python tests under `core/engine/tests` when testing `core/engine`
- Clear test names such as `test_function_name`
- Raw output printed when it helps inspect real behavior
- Any generated test output files stored under `.skillpilot/tests`

## Key Principles

- Default to real code tests
- Only use mock-up tests when the user explicitly asks
- Use pytest for Python tests in `core/engine/tests`
- Keep test names simple and direct
- Print raw output when inspecting behavior is part of the test goal

## Common Issues

- Wrong default:
  if the user did not explicitly ask for mock-up testing, use real code tests
- Wrong location for Python tests:
  place `core/engine` Python tests under `core/engine/tests`
- Hidden stdout in pytest:
  use a runner mode that shows raw output when the user wants to inspect it

## References

- For real code tests, refer to `references/real-code-test.md`
- For mock-up tests, refer to `references/mock-up-test.md`
