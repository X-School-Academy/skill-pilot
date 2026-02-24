---
name: dev-swarm-stage-personas
description: Create/Update detailed user personas and user stories based on market research and business requirements. Use when starting stage 02 (personas) or when user asks to create/update personas, user stories, or user journey maps.
---

# Stage 02 - Personas

Create/Update detailed user personas and user stories to deeply understand target users' needs, behaviors, pain points, and goals.

## When to Use This Skill

- User asks to start stage 02 (personas)
- User wants to create/update user personas or user stories
- User wants to map user journeys or empathy maps

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/` folder has content (not just `.gitkeep`)
2. Check if `01-market-research/` folder has content
3. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` - All markdown files
- `01-market-research/*.md` - All markdown files

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `02-personas/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve
- Why user personas are critical for product success
- How this builds upon previous stages
- What deliverables will be produced

#### 2.2 File Selection

Select files from these options based on project needs:

**User Research & Personas:**
- `personas.md` - Detailed user personas with demographics, behaviors, motivations
- `pain-points.md` - Comprehensive list of user pain points
- `empathy-maps/` - Diagrams visualizing what users say, think, do, and feel

**User Stories & Journeys:**
- `user-stories.md` - Stories in "As a [persona], I want to [action], so that [benefit]" format
- `user-journey-maps/` - Journey diagrams showing user interactions
- `use-cases.md` - Detailed use cases for different personas

For each selected file, provide:
- Short description
- Why it's essential for this project
- Key information it should include

**Note:** Not all files may be necessary. Select based on project complexity.

#### 2.3 Request User Approval

Ask user: "Please check the Stage Proposal in `02-personas/README.md`. Update it directly or tell me how to update it."

### Step 3: Execute Stage Plan

Once user approves `02-personas/README.md`:

#### 3.1 Create All Planned Files

Create each file listed in the approved README:

- **For `.md` files:** Write comprehensive, well-structured content based on insights from previous stages
- **For diagram folders:** Follow `dev-swarm/docs/mermaid-diagram-guide.md` to create the related diagrams files

**Quality Guidelines:**
- Base personas on real insights from market research, not assumptions
- Create 3-5 distinct personas representing different user segments
- Ensure user stories are specific, measurable, and actionable
- Include both primary and secondary personas if relevant
- Map pain points to specific personas
- Connect user journeys to business goals

#### 3.2 Request User Approval for Files

After creating all files:
- Provide a summary of what was created
- Highlight key insights from the personas
- Ask: "Please review the personas and user stories. You can update or delete files, or let me know how to modify them."

### Step 4: Finalize Stage

Once user approves all files:

#### 4.1 Documentation Finalization
- Sync `02-personas/README.md` to remove any deleted files
- Ensure all files are complete and well-formatted
- Verify personas align with market research findings
- Confirm user stories cover key use cases
- Check that all diagrams render correctly

#### 4.2 Prepare for Next Stage
- Summarize key personas and insights for reference in later stages
- Identify which personas should be prioritized for MVP (stage 03)
- Note any open questions or assumptions needing validation

#### 4.3 Announce Completion

Inform user:
- "Stage 02 (Personas) is complete"
- Summary of deliverables created
- Key insights discovered
- "Ready to proceed to Stage 03 (MVP) when you are"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Base personas on research data, not assumptions
- Keep personas specific and actionable
- Connect personas to business goals
- Support smooth transition to MVP definition
