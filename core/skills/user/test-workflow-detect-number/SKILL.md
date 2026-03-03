---
name: test-workflow-detect-number
description: Check a user-provided string for digits and return the numeric content as plain text, or return string if no digits exist. Use when testing workflow nodes that inspect text for numbers.
---

# AI Builder - Test Workflow Detect Number

This skill checks whether a user-provided string contains digits and returns the numeric content for workflow testing.

## When to Use This Skill

- You need a workflow test node that inspects text for numeric content
- You want to validate simple text classification in a workflow
- You need a plain-text output that signals whether digits were found

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Inspect the input text and extract numeric characters when present.
- **QA Engineer**: Keep the output rule simple and easy to validate in workflow tests.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Read the Input

Read the user-provided string.

### Step 2: Check for Digits

Inspect the string for numeric characters (`0` through `9`).

### Step 3: Return the Result

If the string contains digits, return the digits in the same order as a plain-text string.

If the string contains no digits, return:

`string`

## Expected Output

Output result as plain text. If the user asked to save it to a file, write it there.

- The extracted digits as a plain-text string when digits exist
- `string` when the input contains no digits

## Key Principles

- Keep the rule deterministic
- Preserve digit order from the input
- Do not add extra explanation unless the user requests it
