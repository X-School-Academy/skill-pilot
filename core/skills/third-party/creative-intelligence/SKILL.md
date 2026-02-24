---
name: creative-intelligence
description: Run structured brainstorming and research workflows to generate, evaluate, and document product or technical ideas using proven frameworks such as SCAMPER, SWOT, 5 Whys, and mind mapping.
compatibility: Requires bash for bundled scripts under scripts/.
---

# AI Builder - Creative Intelligence

Use this skill to drive evidence-based ideation and produce actionable outputs instead of ad-hoc brainstorming.

## When to Use This Skill

- The user asks to brainstorm, ideate, or explore alternatives.
- The task needs research-backed recommendations before implementation.
- You need structured creativity frameworks (for example SCAMPER, SWOT, 5 Whys).
- You must produce reusable outputs such as research notes, idea sets, or prioritized options.

## Your Roles in This Skill

- **Facilitator**: Select and run the right brainstorming method for the goal.
- **Researcher**: Collect and synthesize relevant evidence from docs, code, and trusted web sources.
- **Analyst**: Converge generated ideas into prioritized, actionable recommendations.
- **Technical Writer**: Document methods, assumptions, and outputs clearly using provided templates.

## Role Communication

As an expert in your assigned roles, announce actions before execution using this exact pattern:

`As a {Role, and Role-XYZ if have more roles}, I will {action description}`

## Instructions

### Step 1: Define objective and constraints

1. Clarify the exact decision or problem to solve.
2. Capture success criteria, time constraints, and non-negotiables.
3. Choose whether the session is divergence-first (idea generation) or convergence-first (decision support).

### Step 2: Select method and execute

1. Pick one or more methods based on the objective:
   - SCAMPER for feature variation and concept expansion
   - 5 Whys for root-cause discovery
   - SWOT for strategic framing
   - Mind mapping for structure and relationships
2. Run methods systematically and record all outputs.
3. Use bundled scripts when useful:
   - `bash scripts/scamper-prompts.sh "<topic>"`
   - `bash scripts/swot-template.sh > swot-analysis.md`
   - `bash scripts/research-sources.sh`

### Step 3: Run focused research

1. Gather evidence relevant to the generated ideas.
2. Prefer primary sources (official docs, standards, vendor pages).
3. Tag findings by confidence level and source quality.

### Step 4: Converge to recommendations

1. Group ideas into themes.
2. Score options by impact, feasibility, and risk.
3. Produce top recommendations with tradeoffs and next actions.

### Step 5: Document outputs

1. Use `templates/brainstorm-session.template.md` for ideation sessions.
2. Use `templates/research-report.template.md` for research deliverables.
3. Include assumptions, open questions, and follow-up experiments.

### Step 6: Verify quality before handoff

1. Ensure recommendations are traceable to evidence.
2. Check that rejected alternatives and reasons are documented.
3. Confirm outputs are actionable for the next execution stage.

## References

- Extended guidance: `./REFERENCE.md`
- Methods and frameworks: `./resources/`
- Reusable templates: `./templates/`
