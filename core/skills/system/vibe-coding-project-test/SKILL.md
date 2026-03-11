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

## Project Boundary

The vibe coding project is a separate project located at `workspace/vibe-coding/{project-name}/`. When building, reviewing, testing, or modifying the project, do NOT read or modify files outside of the project folder unless the user explicitly asks.

## Instructions

### Step 1: Read the Implementation Context

Read the referenced `implement.md` and identify the affected flows.

### Step 2: Run Relevant Checks

Use integration testing as the highest priority method. The following list is in priority order — use higher-priority methods first and cover as much code as possible:

1. **Integration testing** (highest priority): Use agent skill `playwright-cli` for end-to-end validation of web pages, interactive flows, and any browser-accessible interfaces. For Flutter projects, use `flutter test integration_test` instead.
2. **HTTP API testing**: Use `curl` for testing any HTTP API endpoints.
3. **WebSocket testing**: Use `wscat` for testing WebSocket connections. Install with `pnpm install -g wscat` if not available.
4. **Unit testing**: Write code tests for major complex logic functions.

Apply whichever methods are relevant to the project. Not every project needs all methods.

### Step 3: Report Results

Summarize passed checks, failed checks, bugs found, and coverage gaps.
