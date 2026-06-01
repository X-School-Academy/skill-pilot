# Use Cases

Use this reference to map the user's request to the right Architecture Explorer mode and output.

## Understand a Project

Use when the user wants to know what an existing repo does or how it works.

Recommended mode: Quick Mode for a fast overview, Deep Mode for full architecture.

Output should include:

- Plain-language summary.
- Main modules and responsibilities.
- Main runtime flow.
- Core workflows.
- Mermaid component diagram.
- Evidence for important claims.

## Reverse-Engineer Architecture

Use when the user asks for architecture, system design, boundaries, or component relationships.

Recommended mode: Deep Mode.

Output should include:

- Language-independent architecture.
- Current tech stack mapping.
- Module map.
- Interface and boundary map.
- Runtime and deployment view.
- Evidence map.

## Rebuild or Convert a Project

Use when the user wants to remake the project in another language, framework, or stack.

Recommended mode: Remake Mode.

Output should include:

- Behavior that must be preserved.
- What can change in the target stack.
- Language-independent module list.
- API contract.
- Data model contract.
- Workflow contract.
- Error behavior contract.
- Security/auth rules.
- Suggested implementation phases.
- Test plan.
- Prompt for another AI coding agent.

## Generate Diagrams

Use when the user asks for Mermaid diagrams, architecture diagrams, workflow diagrams, or data-flow diagrams.

Recommended mode: Quick Mode for one or two diagrams, Deep Mode for a diagram package.

Output should include:

- System context diagram.
- Component map.
- Main workflow sequence diagram.
- Data flow diagram when useful.
- Short explanation and file evidence for each diagram.

Do not create diagrams from file names alone. Trace workflows first.

## Expert Review

Use when the user wants design, performance, security, maintainability, scalability, testing, or AI-agent-readiness evaluation.

Recommended mode: Expert Review Mode.

Output should include:

- Evidence-based findings.
- Severity for each issue.
- Why each issue matters.
- Language-independent fix.
- Current-stack fix.
- Uncertain points separated from confirmed issues.

## Learning From a Codebase

Use when the user wants to study the project, teach junior developers, create exercises, or turn the repo into a learning path.

Recommended mode: Learning Mode.

Output should include:

- Beginner explanation.
- Concepts to learn first.
- Suggested reading order.
- Guided exploration tasks.
- Debugging exercises.
- Small remake exercises.
- Design review questions.

## Documentation From Source

Use when the user wants architecture docs, onboarding docs, implementation notes, or a package of project documentation generated from the repo.

Recommended mode: Deep Mode.

Output should include:

- Executive summary.
- Architecture sections.
- Diagrams.
- Module map.
- Workflow docs.
- Runtime/deployment docs.
- Evidence and uncertainty notes.

## Focused Investigation

Use when the user gives a specific focus such as frontend, backend, API, database, authentication, deployment, performance, security, or one workflow.

Recommended mode: The mode that matches the focus:

- Expert Review Mode for risks and quality.
- Remake Mode for conversion.
- Learning Mode for teaching.
- Quick Mode for a focused overview.
- Deep Mode when the focus still needs a complete package.

Output should stay focused on the requested area while still separating language-independent design from current implementation details.
