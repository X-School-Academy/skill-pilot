---
name: vibe-coding-project-test
description: Test a Vibe Coding project implementation using its implement.md context and the current codebase. Use when the user wants validation, bug discovery, or test coverage for an implementation.
---

# AI Builder - Vibe Coding Project Test

Test a Vibe Coding project implementation and report the results.

## When to Use This Skill

- The user asks to test the implementation
- The project has `implement.md` context
- The goal is validation, bug discovery, or missing coverage analysis

## Your Roles in This Skill

- **QA Engineer**: Design and run the test pass
- **Backend Developer**: Interpret failures and likely root causes

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

### Step 1: Read the Implementation Context

Read the referenced `implement.md` and identify the affected flows.

### Step 2: Run Relevant Checks

Execute the most relevant tests, targeted manual checks, or static validation for the touched functionality.

### Step 3: Report Results

Summarize passed checks, failed checks, bugs found, and coverage gaps.
