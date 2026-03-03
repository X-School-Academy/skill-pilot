---
name: test-workflow-random-string
description: Produce a random string as plain text output. Use when testing workflow nodes that need a simple text result.
---

# AI Builder - Test Workflow Random String

This skill generates one random string for workflow testing.

## When to Use This Skill

- You need a workflow test node that returns text
- You want a simple upstream string value for downstream workflow steps
- You need to verify plain-text text output handling in workflow execution

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Generate the random text output in a clean, consistent format.
- **QA Engineer**: Ensure the output remains simple and easy to validate in workflow runs.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Generate the Value

Create one random alphanumeric string.

### Step 2: Return the Result

Return only the generated string unless the user explicitly asks for a short label or explanation.

## Expected Output

Output result as plain text. If the user asked to save it to a file, write it there.

- A single random alphanumeric string as plain text

## Key Principles

- Keep the response concise
- Do not add formatting that makes downstream parsing harder
- Do not include extra commentary unless the user requests it
