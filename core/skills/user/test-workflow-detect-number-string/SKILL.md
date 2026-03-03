---
name: test-workflow-detect-number-string
description: Inspect a provided string and output the numeric characters if present, otherwise output the word string. Use when validating workflow text inspection and conditional plain-text output.
---

# AI Builder - Test Workflow Detect Number String

This skill checks an input string for numeric characters and returns a simple plain-text result for workflow testing.

## When to Use This Skill

- You need a workflow node that inspects string content
- You want to test conditional output based on whether digits are present
- You want a downstream-friendly plain-text result

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Inspect the input text and derive the correct plain-text output.
- **QA Engineer**: Ensure the result is simple, deterministic, and easy for downstream workflow nodes to consume.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Read the Input

1. Read the user-provided string.
2. Treat the full provided text as the input unless the user clearly marks a specific substring to inspect.

### Step 2: Inspect for Numbers

1. Check whether the input contains any numeric characters (`0-9`).
2. If numeric characters are present, extract and return the numeric characters as plain text.
3. If no numeric characters are present, return `string`.

### Step 3: Return the Result

1. Output result as plain text. If the user asked to save it to a file, write it there.
2. If no file write was requested, return only the extracted digits or `string` with no labels, bullets, code fences, or explanation.

## Expected Output

- The numeric characters found in the input as plain text, or `string` if none are present
