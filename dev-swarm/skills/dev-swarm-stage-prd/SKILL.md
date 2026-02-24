---
name: dev-swarm-stage-prd
description: Create a comprehensive Product Requirements Document defining complete product behavior, functional and non-functional requirements, and user flows. Use when starting stage 05 (prd) or when user asks to define product requirements or acceptance criteria.
---

# Stage 05 - PRD (Product Requirements Document)

Create a comprehensive Product Requirements Document that defines the complete product behavior, including functional requirements, non-functional requirements, user flows, acceptance criteria, and all specifications needed to guide development.

## When to Use This Skill

- User asks to start stage 05 (prd)
- User wants to define product requirements or acceptance criteria
- User asks about functional or non-functional requirements

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/` through `04-tech-research/` folders have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` through `04-tech-research/*.md` - All markdown files

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `05-prd/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve
- Why a comprehensive PRD is critical for successful development
- How this builds upon previous stages
- What deliverables will be produced

#### 2.2 File Selection

Select files from these options based on project needs:

**Core Requirements:**
- `functional-requirements.md` - Detailed functional requirements describing what the system must do
- `non-functional-requirements.md` - Performance, security, scalability, and other quality attributes

**User Experience & Flows:**
- `user-flows/` - User interaction flow diagrams

**Quality & Validation:**
- `acceptance-criteria.md` - Clear, testable criteria for each feature
- `error-handling-and-edge-cases.md` - How the system handles errors and boundary conditions

**Data & Analytics:**
- `analytics-and-events.md` - Events to track and metrics to collect

**Compliance & Legal:**
- `compliance-and-legal-notes.md` - Regulatory requirements and legal considerations

**Dependencies:**
- `dependencies.md` - External services, APIs, and third-party integrations

For each selected file, provide:
- Short description
- Why it's essential for this project
- Key information it should include

#### 2.3 Request User Approval

Ask user: "Please check the Stage Proposal in `05-prd/README.md`. Update it directly or tell me how to update it."

### Step 3: Execute Stage Plan

Once user approves `05-prd/README.md`:

#### 3.1 Create All Planned Files

Create each file listed in the approved README:

- **For `.md` files:** Write comprehensive content based on insights from all previous stages
- **For diagram folders:** Follow `dev-swarm/docs/mermaid-diagram-guide.md` to create related diagrams files

**Quality Guidelines:**
- Base requirements on personas, user stories, MVP scope, and tech research findings
- Write functional requirements that are specific and testable
- Define non-functional requirements with quantifiable targets
- Ensure acceptance criteria use clear Given/When/Then format
- Include both happy path and error scenarios in user flows
- Incorporate any constraints discovered during tech research

#### 3.2 Request User Approval for Files

After creating all files:
- Provide a summary of what was created
- Highlight key requirements and critical dependencies
- Ask: "Please review the PRD documents. You can update or delete files, or let me know how to modify them."

### Step 4: Finalize Stage

Once user approves all files:

#### 4.1 Documentation Finalization
- Sync `05-prd/README.md` to remove any deleted files
- Ensure all files are complete and well-formatted
- Check that all diagrams render correctly

#### 4.2 Prepare for Next Stage
- Summarize key requirements for reference in UX and Architecture stages
- Identify requirements that will impact UX design decisions

#### 4.3 Announce Completion

Inform user:
- "Stage 05 (PRD) is complete"
- Summary of deliverables created
- Key requirements and constraints identified
- "Ready to proceed to Stage 06 (UX) when you are"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Make requirements specific and testable
- Include clear acceptance criteria
- Cover both happy path and error scenarios
- Support smooth transition to UX design
