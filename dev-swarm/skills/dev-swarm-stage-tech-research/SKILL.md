---
name: dev-swarm-stage-tech-research
description: Validate technical feasibility through proof of concepts, technology spikes, and prototypes before committing to full development. Use when starting stage 04 (tech-research) or when user asks to validate technical assumptions or create PoCs.
---

# Stage 04 - Tech Research

Validate technical feasibility and reduce project risk by conducting proof of concepts (PoCs), technology spikes, API evaluations, and performance benchmarks before committing to full product development.

## When to Use This Skill

- User asks to start stage 04 (tech-research)
- User wants to validate technical assumptions or feasibility
- User asks about proof of concepts, technology spikes, or prototypes
- User needs to evaluate third-party APIs or services
- User wants to test critical technical paths before full development

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/`, `01-market-research/`, `02-personas/`, `03-mvp/` folders have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` through `03-mvp/*.md` - All markdown files

Identify:
- Core technical requirements from MVP features
- Critical technical assumptions that need validation
- Third-party services or APIs mentioned
- Performance-sensitive operations
- Novel or unfamiliar technologies in scope

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `04-tech-research/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What technical risks or assumptions need validation
- Why this research is critical before committing to full development
- How this will inform architecture and technical decisions
- What go/no-go decisions will be made based on findings

#### Research Execution Rules

**Folder Structure Rules:**
1. **Atomic:** Each research topic must be in a separate folder/project, independently
2. **No Code Sharing:** Even if two research topics use the same framework/scaffolding, keep them in separate folders as different projects (e.g., two Next.js UI tests = two separate Next.js project setups)
3. **Third-party APIs:** Fetch latest docs from internet and save key information in the research folder
4. **Code + Tests:** Each research must include working code with tests to prove tech assumptions

#### 2.2 File Selection

#### 2.2 Research Topic Selection Criteria

**CRITICAL: Avoid Over-Research/Over-Testing**

Research should be **minimal and focused**. Only research topics that meet these criteria:

**✅ DO Research When:**
1. **Unfamiliarity:** Technologies/approaches you are not familiar with
2. **Rarity:** Technologies rarely used by other developers (limited community knowledge)
3. **Poor Documentation:** Technologies with sparse community discussion/examples
4. **Error-Prone:** Technologies known to be easy to misconfigure or implement incorrectly
5. **Third-Party Uncertainty:** Unsure about third-party APIs/SDKs/packages capabilities or limitations
6. **Business-Critical Path:** Core functionality that could make/break the project
7. **Performance Constraints:** Features with specific performance requirements that need validation

**❌ DON'T Research When:**
- Standard, well-documented frameworks (React, Express, Django, etc.)
- Common CRUD operations with established patterns
- Technologies you've used successfully in similar projects
- Well-supported mainstream libraries with extensive documentation
- Simple integrations with major platforms (Stripe, Auth0, AWS basics)

**Research Scope Limit:** Keep research to **2-5 topics maximum** per project. Focus only on the highest-risk unknowns.

**Proposed Research Topics:** (Research folders will be created after approval)

For each proposed research topic, clearly specify:

- `research-1-name/` 
  - **What:** [Specific technology/API/integration to be tested]
  - **Why:** [Why this needs research - which selection criteria it meets]
  - **Validation Goal:** [What specific assumption or risk will be validated]

- `research-2-name/` 
  - **What:** [Specific technology/API/integration to be tested]
  - **Why:** [Why this needs research - which selection criteria it meets] 
  - **Validation Goal:** [What specific assumption or risk will be validated]

- ...

**Example:**
- `research-webrtc-streaming/`
  - **What:** WebRTC peer-to-peer video streaming with screen sharing
  - **Why:** Unfamiliar technology with complex NAT traversal and browser compatibility issues
  - **Validation Goal:** Prove that reliable P2P connections can be established between users

**Research Results:** (Created after each research completion)
- `research-1-name-results.md` - Summary of research result - API docs, code snippets used for the next stage  
- `research-2-name-results.md` - Summary of research result - API docs, code snippets used for the next stage
- ... 


#### 2.3 Request User Approval

Ask user: "Please check the Stage Proposal in `04-tech-research/README.md`. Update it directly or tell me how to update it."

### Step 3: Create All Research READMEs

Once user approves `04-tech-research/README.md`:

#### 3.1 Create All Research README Files

For **each** research topic in the approved plan, create the README file:

- Create research project folder `research-x-name/`
- Create project `research-x-name/README.md`
- In the `README.md`, outline the project:
  - **Research Goal:** What specific assumption or risk is being validated.
  - **Research Details:** Implementation plan and approach.
  - **Tools & Frameworks:** Recommend appropriate project manage tool and test framework based on the research type (e.g., `pnpm` for Node.js, `uv` for Python, `cmake` for C++, `pytest` for Python testing, `jest` for JS testing, `playwright` for web UI testing, etc.).

**Create ALL research README files before requesting approval.**

#### 3.2 Request Approval for All Research Plans

After creating all `research-x-name/README.md` files:
- Provide a summary of all research plans created
- Ask user: "I have created research plans for all topics. Please review and update each `research-x-name/README.md` if needed. Let me know when you approve them to start implementation."

### Step 4: Execute Research Topics Sequentially

Once user approves all research README files:

#### 4.1 Implement Each Research Topic (One at a Time)

For each research topic in the approved plan:

**Step A: Implement & Test**
- Set up project scaffolding and install dependencies.
- Implement the minimal code snippets to test assumptions.
- Execute automated tests to verify the proof of concept.
- Document findings and results.

**Step B: Create Results File**
- Write `research-x-name-results.md` with:
  - Summary of research findings
  - API documentation and key information
  - Code snippets for use in next stage
  - Test results and validation
  - Go/no-go recommendations

**Step C: Request Approval**
- Ask user to review the implementation and results.
- Allow user to request modifications or approve to proceed to next research.

#### 4.2 Continue Until All Research Complete

Repeat Step 4.1 for each research topic until all are completed.

### Step 5: Finalize Stage

Once all research topics are completed and user approves:

#### 5.1 Update README with Results
- Update `04-tech-research/README.md` to reflect all completed research
- Add links to all research folders and results files
- Include summary of key findings and decisions

#### 5.2 Documentation Finalization
- Ensure all research folders have working code and tests
- Verify all results files are complete and well-formatted
- Confirm all third-party API documentation is saved

#### 5.3 Prepare for Next Stage
- Summarize validated technical decisions for architecture stage
- Document any constraints discovered that affect PRD or UX
- List technology choices confirmed by research
- Compile all code snippets and examples for reference

#### 5.4 Announce Completion

Inform user:
- "Stage 04 (Tech Research) is complete"
- Summary of research topics completed and deliverables created
- Key findings and validated assumptions
- Any blocking issues or pivots needed
- "Ready to proceed to Stage 05 (PRD) when you are"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- **Avoid Over-Research:** Only research genuine unknowns and high-risk areas
- **Time-Box Everything:** Max 2-4 hours per research topic
- **Minimal Viable Proof:** Just enough code to validate the assumption
- **Fail Fast:** Better to discover blockers now than after full development
- **Focus on Risk:** Research should reduce project risk, not create busy work
- **Document Decisions:** Clear go/no-go recommendations based on evidence
- **Stop When Clear:** If research proves feasibility quickly, stop and move on
