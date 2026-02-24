---
name: dev-swarm-stage-sprints
description: Plan and execute agile development sprints, breaking down product requirements into manageable backlogs with clear acceptance criteria and test plans. Use when starting stage 10 (sprints) or when user asks about sprint planning or backlog creation.
---

# Stage 10 - Sprints

Plan and execute agile development sprints, breaking down the product requirements into manageable backlogs with clear acceptance criteria, developer test plans, and QA verification points to deliver incremental, demo-able product milestones.

## When to Use This Skill

- User asks to start stage 10 (sprints)
- User wants to plan sprints or create backlogs
- User asks about feature development or sprint execution

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/` through `09-devops/` folders have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## AI-Driven Development Sprint and Backlog Guidelines

See `dev-swarm/docs/sprint-backlog-guidelines.md` & `dev-swarm/docs/what-is-a-feature.md`

## Instructions

**Checklist formatting rule:** Any checklist, acceptance criteria, or test plan must use Markdown task lists (e.g., `- [ ] item`) so QA can mark verification status.

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` through `09-devops/*.md` - All markdown files

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `10-sprints/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve (sprint planning, backlog creation, development execution)
- Why agile sprint development is critical for iterative delivery
- How this transforms technical specifications into working software
- What deliverables will be produced

#### 2.2 Sprint Overview

Provide a high-level sprint breakdown:
- **Total number of sprints** planned for MVP delivery
- **Sprint naming convention**: `SPRINT-XX-descriptive-name/` (e.g., `SPRINT-01-user-auth/`)
- **Brief description** of what each sprint will deliver

#### 2.3 Backlog Naming Convention

Explain the backlog file naming convention:
- Format: `[BACKLOG_TYPE]-XX-[feature-name]-<sub-feature>.md`
- BACKLOG_TYPE: `FEATURE`, `CHANGE`, `BUG`, or `IMPROVE`
- XX: Two-digit sequence number (01, 02, etc.)
- feature-name: The feature this backlog relates to
- sub-feature: Optional sub-feature specifier
- Example: `FEATURE-01-user-auth-login.md`, `BUG-02-user-auth-session.md`

#### 2.4 Request User Approval

Ask user: "Please check the Stage Proposal in `10-sprints/README.md`. Update it directly or tell me how to update it."

### Step 3: Create Development Plan

Once user approves README.md, create `10-sprints/development-plan.md`:

**Sprint Breakdown:**
For each sprint, document:
- Sprint number and name
- Sprint goal (one sentence)
- Features/backlogs included
- Dependencies on previous sprints
- Demo criteria
- QA test plan (checkbox list)

**Backlog Details:**
For each backlog item, document:
- Backlog ID and unique keywords
- User story format
- Acceptance criteria (checkbox list)
- Developer test plan (checkbox list)
- Related files from previous stages
- Estimated complexity (S/M/L)

### Step 4: Create Sprint Folders and Backlogs

Once user approves the development plan:

#### 4.1 Create Sprint Folders

For each sprint, create:
```
10-sprints/SPRINT-XX-descriptive-name/
├─ README.md                                          # Sprint overview
└─ [BACKLOG_TYPE]-XX-[feature-name]-<sub-feature>.md  # Individual backlogs
```

Example:
```
10-sprints/SPRINT-01-user-auth/
├─ README.md
├─ FEATURE-01-user-auth-login.md
├─ FEATURE-02-user-auth-register.md
└─ FEATURE-03-user-auth-session.md
```

#### 4.2 Sprint README.md Structure

Each sprint's README.md should contain:
- Sprint status (pending/in_progress/completed/blocked)
- Sprint goal
- Dependencies
- Backlogs with status and complexity
- Sprint test plan (checkbox list)
- Demo script
- Success criteria (checkbox list)

#### 4.3 Backlog File Structure

Each backlog file should contain:
- Keywords (unique across project)
- User story
- Related documentation references
- Acceptance criteria (checkbox list)
- Technical implementation notes
- Developer test plan (checkbox list)
- Dependencies
- Complexity estimate
- Status checklist (checkbox list)

### Step 5: Finalize Sprint Documentation

Once user approves all sprint and backlog files:

#### 5.1 Documentation Finalization
- Sync `10-sprints/README.md` to remove any deleted files
- Ensure all backlog keywords are unique across the project
- Verify all backlogs trace back to PRD requirements
- Confirm all test plans are complete

#### 5.2 Announce Documentation Complete

Inform user:
- "Sprint planning documentation is complete and ready for development"
- Summary of sprints and backlogs created
- Total estimated complexity
- Recommended sprint order

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Each backlog must be independently testable
- Each sprint must be demo-able
- Document all dependencies clearly
- Trace all backlogs to PRD requirements
- Support smooth transition to deployment
