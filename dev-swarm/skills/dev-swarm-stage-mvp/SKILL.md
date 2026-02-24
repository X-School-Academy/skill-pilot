---
name: dev-swarm-stage-mvp
description: Define the Minimum Viable Product scope, prioritize features, and establish success criteria to deliver the smallest testable product. Use when starting stage 03 (mvp) or when user asks to define MVP scope or prioritize features.
---

# Stage 03 - MVP

Define the Minimum Viable Product scope, prioritize features, establish success criteria, and create a focused roadmap to deliver the smallest testable product that validates core assumptions.

## When to Use This Skill

- User asks to start stage 03 (mvp)
- User wants to define MVP scope or prioritize features
- User asks about feature prioritization or release planning

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/`, `01-market-research/`, `02-personas/` folders have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` - All markdown files
- `01-market-research/*.md` - All markdown files
- `02-personas/*.md` - All markdown files

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `03-mvp/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve
- Why defining MVP scope is critical for product success
- How this builds upon previous stages
- What deliverables will be produced

#### 2.2 File Selection

Select files from these options based on project needs:

**Core MVP Definition:**
- `mvp-features.md` - Core MVP features that must be included for initial launch
- `feature-prioritization.md` - Feature priority matrix using MoSCoW or similar framework
- `mvp-roadmap/` - Roadmap diagrams showing MVP development phases

**Scope Management:**
- `mvp-scope.md` - Explicit in-scope features with acceptance criteria
- `out-of-scope.md` - Features explicitly deferred to future versions

**Success & Release:**
- `success-criteria.md` - Measurable MVP success criteria
- `release-plan.md` - MVP release plan including launch strategy

For each selected file, provide:
- Short description
- Why it's essential for this project
- Key information it should include

#### 2.3 Request User Approval

Ask user: "Please check the Stage Proposal in `03-mvp/README.md`. Update it directly or tell me how to update it."

### Step 3: Execute Stage Plan

Once user approves `03-mvp/README.md`:

#### 3.1 Create All Planned Files

Create each file listed in the approved README:

- **For `.md` files:** Write comprehensive content based on insights from previous stages
- **For diagram folders:** Follow `dev-swarm/docs/mermaid-diagram-guide.md` to create related diagrams files

**Quality Guidelines:**
- Base MVP features on validated user pain points from personas
- Use market research to identify competitive differentiation
- Apply feature prioritization frameworks (MoSCoW, RICE, Kano)
- Ensure MVP scope is achievable and focused
- Include clear rationale for what's in-scope vs out-of-scope

#### 3.2 Request User Approval for Files

After creating all files:
- Provide a summary of what was created
- Highlight the core MVP value proposition
- List key features included and excluded
- Ask: "Please review the MVP definition. You can update or delete files, or let me know how to modify them."

### Step 4: Finalize Stage

Once user approves all files:

#### 4.1 Documentation Finalization
- Sync `03-mvp/README.md` to remove any deleted files
- Ensure all files are complete and well-formatted
- Check that all diagrams render correctly

#### 4.2 Prepare for Next Stage
- Summarize MVP scope for reference in later stages
- Identify key technical requirements implied by MVP features

#### 4.3 Announce Completion

Inform user:
- "Stage 03 (MVP) is complete"
- Summary of deliverables created
- Core MVP features and scope boundaries
- "Ready to proceed to Stage 04 (Tech Research) when you are"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Focus on smallest testable product
- Base features on validated user needs
- Keep scope achievable and focused
- Support smooth transition to PRD definition
