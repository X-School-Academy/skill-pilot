---
name: test-workflow-random-number
description: Produce a random number as plain text output. Use when testing workflow nodes that need a simple numeric result.
---

# AI Builder - Test Workflow Random Number

This skill generates one random number for workflow testing.

## When to Use This Skill

- You need a workflow test node that returns a number
- You want a simple upstream numeric value for downstream workflow steps
- You need to verify plain-text output handling in workflow execution

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Generate the random numeric output in a simple, reliable format.
- **QA Engineer**: Keep the output minimal and easy to validate in workflow tests.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Generate the Value

Create one random integer.

### Step 2: Return the Result

Return only the generated number unless the user explicitly asks for a short label or explanation.

## Expected Output

Output result as plain text. If the user asked to save it to a file, write it there.

- A single random integer as plain text

## Key Principles

- Keep the response concise
- Do not add formatting that makes downstream parsing harder
- Do not include extra commentary unless the user requests it
