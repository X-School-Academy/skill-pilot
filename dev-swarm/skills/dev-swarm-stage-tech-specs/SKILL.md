---
name: dev-swarm-stage-tech-specs
description: Create detailed technical specifications translating architecture designs into implementation-ready documents, including API specs, database migrations, and testing strategies. Use when starting stage 08 (tech-specs) or when user asks about technical specifications or OpenAPI docs.
---

# Stage 08 - Tech Specs

Create detailed technical specifications that translate architecture designs into implementation-ready documents, covering API contracts, database migrations, frontend/backend specs, testing strategies, and security requirements.

## When to Use This Skill

- User asks to start stage 08 (tech-specs)
- User wants to create technical specifications or OpenAPI docs
- User asks about API specs, testing strategy, or service specifications

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/` through `07-architecture/` folders have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` through `07-architecture/*.md` - All markdown files

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `08-tech-specs/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve
- Why detailed technical specifications are critical before development
- How this bridges architecture design (stage 07) with implementation (stage 10 sprints)
- What deliverables will be produced

#### 2.2 File Selection

Select files from these options based on project needs:

**Overview & Strategy:**
- `tech-specs-overview.md` - Technical specifications overview
- `testing-strategy.md` - Comprehensive testing strategy (unit, integration, e2e)
- `error-handling.md` - Error handling strategy

**API Specifications:**
- `api-specifications.md` - Detailed API specifications with request/response formats
- `openapi.yaml` - OpenAPI/Swagger specification for REST APIs
- `api-mockup-adapter.md` - Design for configurable mock adapters for cost/latency-sensitive third-party services. Refer to `references/api-mockup-adapter.md` for design instructions.

**Database Specifications:**
- `database-migrations.md` - Database migration strategy

**Frontend Specifications:**
- `frontend-specs.md` - Frontend technical specs (language, framework, coding standards)
- `state-management-strategy.md` - How frontend handles state

**Backend Specifications:**
- `backend-specs.md` - Backend technical specs (language, framework, coding standards)
- `service-specs/` - Individual service specification files (auth, payment, etc.)

**Dependencies & Integrations:**
- `dependencies-list.md` - Comprehensive list of planned packages
- `third-party-integration-guide.md` - Third-party integration specifications

**Security & Performance:**
- `security-specifications.md` - Security implementation details
- `performance-specs.md` - Performance requirements

**Observability:**
- `observability-spec.md` - Logging, metrics, tracing specifications

For each selected file, provide:
- Short description
- Why it's essential for this project
- Key information it should include

#### 2.3 Request User Approval

Ask user: "Please check the Stage Proposal in `08-tech-specs/README.md`. Update it directly or tell me how to update it."

### Step 3: Execute Stage Plan

Once user approves `08-tech-specs/README.md`:

#### 3.1 Create All Planned Files

Create each file listed in the approved README:

- **For `.md` files:** Write comprehensive, implementation-ready specifications. For `api-mockup-adapter.md`, refer to `references/api-mockup-adapter.md` for design guidance.
- **For `.yaml` files:** Create valid OpenAPI/Swagger specifications
- **For `service-specs/` folder:** Create individual service specification files

**Quality Guidelines:**
- Ensure all specifications are consistent with architecture decisions
- API specifications must include request/response examples and error codes
- All specs should be detailed enough for developers to implement without ambiguity
- Include code examples where applicable

#### 3.2 Request User Approval for Files

After creating all files:
- Provide a summary of what was created
- Highlight key technical decisions documented
- Ask: "Please review the technical specifications. You can update or delete files, or let me know how to modify them."

### Step 4: Finalize Stage

Once user approves all files:

#### 4.1 Documentation Finalization
- Sync `08-tech-specs/README.md` to remove any deleted files
- Ensure all files are complete and well-formatted
- Validate API specifications follow OpenAPI standards

#### 4.2 Prepare for Next Stage
- Summarize key technical specifications for reference in DevOps setup
- Identify infrastructure requirements derived from the specs

#### 4.3 Announce Completion

Inform user:
- "Stage 08 (Tech Specs) is complete"
- Summary of deliverables created
- Key technical decisions documented
- "Ready to proceed to Stage 09 (DevOps) when you are"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Make specifications implementation-ready
- Include code examples where helpful
- Ensure consistency with architecture decisions
- Support smooth transition to DevOps setup
