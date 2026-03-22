---
name: skill-pilot-feature-test
description: Test a Skill Pilot feature implementation and report the results. Use when a feature needs validation before merge.
---

# AI Builder - Skill Pilot Feature Test

Test a feature implementation and report the outcome.

## When to Use This Skill

- The feature should be validated
- The user wants bugs found or confidence increased

## Your Roles in This Skill

- **QA Engineer**: Run the relevant tests
- **Backend Developer**: Interpret failures

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Feature Context

The feature's `requirements.md` may list related feature files under `core/features/`. When referenced, read only the mentioned feature files for context — do not read all files in `core/features/`. If a file has already been loaded in this session, do not read it again unless it was updated or the user asks.

## Instructions

### Step 1: Read the implementation context

Read the referenced implementation file.

### Step 2: Test the feature

Use integration testing as the highest priority method. The following list is in priority order — use higher-priority methods first and cover as much code as possible:

1. **Integration testing** (highest priority): Use web browser agent skill for end-to-end validation of web pages, interactive flows, and any browser-accessible interfaces. For Flutter projects, use `flutter test integration_test` instead.
2. **HTTP API testing**: Use `curl` for testing any HTTP API endpoints.
3. **WebSocket testing**: Use `wscat` for testing WebSocket connections. Install with `pnpm install -g wscat` if not available.
4. **Unit testing**: Write code tests for major complex logic functions.

Apply whichever methods are relevant to the feature. Not every feature needs all methods.

### Step 3: Report Results

Summarize passed checks, failed checks, bugs found, and coverage gaps.
