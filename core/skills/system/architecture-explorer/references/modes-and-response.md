# Modes and Response Formats

Use this reference to choose the right output mode and final response.

## Quick Mode

Use when the user wants a fast understanding.

Output:

- What the project does.
- Main modules.
- One Mermaid component diagram.
- One main workflow.
- Top 5 risks.
- Remake summary.

## Deep Mode

Use when the user wants full reverse engineering.

Output the full package described in `output-package.md`.

## Remake Mode

Use when the user wants to rebuild the project in another language.

Focus on:

- Language-independent behavior.
- API contract.
- Data model.
- Workflow contract.
- Test plan.
- Target language implementation strategy.

## Expert Review Mode

Use when the user wants design/performance/security evaluation.

Focus on:

- Evidence-based issues.
- Severity.
- Why it matters.
- Language-independent fix.
- Current-stack fix.

## Learning Mode

Use when the user wants to learn from the project.

Focus on:

- Beginner explanation.
- Reading path.
- Learning tasks.
- Debugging tasks.
- Small remake exercises.

## Final Response Format

When finishing the skill run, respond with:

```text
Architecture Explorer completed.

I produced:
- Language-independent architecture summary
- Current tech stack map
- Module map
- Core workflows
- Data model
- Mermaid diagrams
- Design/performance review
- Remake guide
- Learning guide
- Evidence map

Most important finding:
<one-sentence summary>

Best next action:
<recommended next step>
```

If the user wants to rebuild the project, provide a next prompt:

```text
Use the remake guide to rebuild this project in <target language/framework>.
First create the module plan, API contract, data model, workflow plan, and test plan.
Do not start implementation until the plan is approved.
```
