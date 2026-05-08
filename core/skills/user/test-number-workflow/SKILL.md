---
name: test-number-workflow
description: Produce simple number and string outputs for workflow tests. Use when testing workflow nodes that need random numbers, random strings, number-string concatenation, digit extraction, or conditional plain-text number detection.
---

# AI Builder - Test Number Workflow

Generate, combine, and inspect simple number/string values for workflow execution tests.

## When to Use This Skill

- A workflow test node needs a random numeric result.
- A workflow test node needs a random string result.
- A workflow test node needs to concatenate a number and a string.
- A workflow test node needs to inspect text and return digits or `string`.
- A workflow needs downstream-friendly plain-text outputs.

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Produce deterministic-format outputs for the requested test action.
- **QA Engineer**: Keep outputs simple, parseable, and suitable for downstream workflow nodes.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Select the Test Action

- If the task asks for a random number, use `references/random-number.md`.
- If the task asks for a random string, use `references/random-string.md`.
- If the task asks to concatenate a number and string, use `references/concat-number-string.md`.
- If the task asks to detect, inspect, or extract numbers from text, use `references/detect-number.md`.

### Step 2: Load the Needed Reference

Open only the reference file for the selected action.

### Step 3: Return the Result

Output result as plain text. If the user asked to save it to a file, write it there.

Unless the selected action explicitly says otherwise, return only the generated or derived value with no labels, bullets, code fences, or explanation.

## Expected Output

- A random integer.
- A random alphanumeric string.
- A concatenated number-string value.
- Extracted digits, or `string` when no digits exist.
