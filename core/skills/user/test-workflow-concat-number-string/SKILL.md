---
name: test-workflow-concat-number-string
description: Combine a user-provided number and string into one plain-text string output. Use when testing workflow nodes that merge simple inputs.
---

# AI Builder - Test Workflow Concat Number String

This skill combines a user-provided number and string into one plain-text result for workflow testing.

## When to Use This Skill

- You need a workflow test node that merges two simple inputs
- You want to validate passing a number and a string through a workflow
- You need a predictable plain-text concatenation output for downstream nodes

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Combine the inputs into one output string exactly as requested.
- **QA Engineer**: Keep the output deterministic and easy to verify in workflow tests.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Read Inputs

Read the user-provided number and the user-provided string.

### Step 2: Concatenate

Combine the number and string into one string.

Use the direct input order:
1. number
2. string

Do not add separators unless the user explicitly requests one.

### Step 3: Return the Result

Return the combined string as plain text.

## Expected Output

Output result as plain text. If the user asked to save it to a file, write it there.

- One concatenated string that contains the number followed by the string

## Key Principles

- Preserve the original input values
- Keep the default behavior simple and predictable
- Do not add extra explanation unless the user requests it
