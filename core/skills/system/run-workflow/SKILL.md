---
name: run-workflow
description: Run a saved workflow JSON through the project workflow runner. Use when the user asks to execute an existing workflow file under core/workflows/ or any workflow path under the project root, or wants to run a workflow with a prompt.
---

# AI Builder - Run Workflow

Run an existing workflow definition through the project workflow runner and report the result clearly.

## When to Use This Skill

- The user asks to run or execute a saved workflow
- The user provides a workflow name, a path under `core/workflows/`, or another workflow file path under the project root
- The user wants to execute a workflow with a new prompt
- The user wants to validate whether a workflow can be run from the CLI

## Your Roles in This Skill

- **Project Manager**: Confirm the requested workflow target and execution intent, then keep the run focused on one workflow invocation.
- **Backend Developer (Engineer)**: Resolve the workflow path, check the runner entry point, and execute the CLI with the correct arguments.
- **Technical Writer**: Report the command used, the workflow path resolved, and the runtime result or blocker in concise language.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Resolve the Workflow Target

1. Accept either:
   - a bare workflow name such as `customer-support-flow`
   - a relative path under `core/workflows/`
   - any relative path under the project root
   - an absolute path that still resolves under the project root
2. If the user gives a bare name, resolve it under `core/workflows/` and append `.json`.
3. Normalize the target to a project-root-relative path when possible.
4. Confirm the resolved file exists before attempting execution.

### Step 2: Validate the Runtime Entry Point

1. Check whether `core/bin/run-workflow` exists and is executable.
2. If it is missing, stop and report that workflow runtime is not implemented yet.
3. Do not include internal implementation details. This skill is only for using the CLI correctly.

### Step 3: Build the Execution Command

1. Use this command shape:
   - `core/bin/run-workflow <workflow-path> <prompt>`
2. Pass the resolved workflow path.
3. Pass the user’s workflow instruction text as the prompt.
4. Do not rewrite the user’s intent beyond minimal cleanup needed for shell-safe execution.

### Step 4: Execute and Capture Output

1. Run the workflow CLI from the repository root.
2. Capture stdout, stderr, and the exit code.
3. If the command fails, report whether the failure is:
   - path resolution
   - validation/runtime error
   - missing runner
   - system execution failure

### Step 5: Report the Result

1. Return:
   - resolved workflow path
   - prompt used
   - command executed
   - exit code
   - concise output summary
2. If the workflow produces structured success output, summarize it briefly.
3. If blocked because the runner is not implemented, say that clearly.

## Key Principles

- Accept workflow files under `core/workflows/` or any valid path under the project root
- Fail fast on missing files or missing runtime entry point
- Keep the run to one workflow per invocation
- Report exact blockers instead of guessing
- Focus on how to use the CLI, not on internal runtime design

## Expected Output

- A single workflow execution attempt, or a clear blocked status if the runner is unavailable
- The exact workflow file used
- The runtime command and its result
