---
name: agent-workflow
description: Create, update, run, resume, or continue agent workflows. Use when the user asks to create or fix workflow JSON, execute an existing workflow, run a workflow with a prompt, resume a workflow run, or continue the next node in a waiting multi-step workflow.
---

# AI Builder - Agent Workflow

Create, update, run, and continue agent workflows while keeping workflow files valid and terminal execution human-in-the-loop aware.

## When to Use This Skill

- The user asks to create, update, fix, review, or convert a process into a workflow JSON file.
- The user asks to run or execute an existing workflow file or named workflow.
- The user asks to resume, recover, or run a workflow with auto-continue behavior.
- The user asks to continue the next node, next agent, or current workflow execution.

## Your Roles in This Skill

- **Project Manager**: Clarify the workflow intent, choose the correct workflow case, and keep each action scoped.
- **Backend Developer (Engineer)**: Apply workflow schema rules, resolve workflow paths, and use the workflow runner safely.
- **QA Engineer**: Validate workflow graph correctness, execution blockers, and final results.
- **Technical Writer**: Report created files, commands, blockers, and outcomes concisely.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Select the Workflow Case

- If creating, updating, fixing, reviewing, or converting a process into workflow JSON, use `references/create-update-workflow.md`.
- If running, executing, resuming, recovering, or validating execution of a saved workflow, use `references/execute-workflow-action.md`.
- If continuing a waiting workflow node or next agent in an active terminal workflow run, use `references/continue-workflow-action.md`.

### Step 2: Load Only the Needed Reference

Open the one reference file that matches the selected case. Load additional references only when that case explicitly requires them.

### Step 3: Execute the Case Instructions

Follow the selected reference file exactly. Keep generated workflow files under `core/workflows/` by default, and keep any temporary or intermediate helper files under `.skillpilot/temp/` unless the user explicitly requested another project-local path.

### Step 4: Verify and Report

Run the validation or execution checks required by the selected case. Report the resulting file path, command, output summary, or blocker in concise language.

## Expected Output

- For create/update cases: a valid workflow JSON file and a short summary of workflow steps and assumptions.
- For run cases: one workflow execution attempt or a clear blocked status, including the resolved workflow path and command result.
- For continue cases: whether the continue signal was accepted, deferred, or blocked.
