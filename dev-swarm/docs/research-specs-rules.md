# Rules for AI Research and Technical Specifications

Purpose: rules for AI agents when conducting research and designing technical specifications. Goals: prevent over-engineering, keep content appropriate to project scale, and respect an expert audience.

## 1. Core principle: context-aware scaling

Golden rule: the depth, length, and complexity of documentation must match the complexity of the project.

- Do not treat a simple script like an enterprise platform.
- Do not treat an open-source tool like a VC-backed startup.
- Do not generate documentation that exceeds the volume of the actual code unless specifically requested.

Project scale definitions and expectations:
- Script, example: `cleanup.sh`
  Expectation: none, or a 1-paragraph README.
- Simple tool, example: `mcp-skill-bridge`
  Expectation: minimal; 1-page tech spec; no market research.
- Library/service, example: auth service
  Expectation: focused; public API docs; simple architecture diagram.
- Application, example: task manager app
  Expectation: standard; PRD; architecture; UI/UX flows.
- Enterprise system, example: banking core
  Expectation: comprehensive; detailed compliance, scaling strategies, etc.

## 2. Audience definition: the expert developer

Target audience: senior software engineer / architect.

What to avoid (the “junior trap”):
- No tutorials: do not explain how `git`, `python`, or `react` works.
- No generic boilerplate: do not copy-paste standard PEP 8 rules or OWASP Top 10 lists; reference them by name only.
- No “why this tech” essays: unless it’s a controversial choice, don’t justify standard choices (example: “Why use Python for scripting?”).

What to provide:
- Decisions: “We chose library X over Y because of Z constraint.”
- Constraints: “Must run on 128MB RAM”, “No external network access”.
- Interfaces: “The API will look like this...”
- Gotchas: “Watch out for circular dependencies in module A.”

## 3. Rules for market research (stage 1)

Rule 3.1: the “open source” exemption
- If the project is an open-source developer tool, utility, or internal script:
  - Skip all market research.
  - Skip all pricing/revenue models.
  - Skip competitor analysis (unless comparing technical features for implementation ideas).
- Action: create `SKIP.md` with a single sentence: “Developer tool; market research not applicable.”

Rule 3.2: validity over volume
- If research is needed (for example, a commercial app), focus on validation, not hallucination.
- Do not invent revenue projections for a pre-MVP idea.
- Do not estimate TAM unless you have real data access.

## 4. Rules for technical specifications (stage 7)

Rule 4.1: conciseness wins
- Tech stack: list dependencies; do not describe them.
  - Bad: “FastAPI is a modern, fast (high-performance), web framework for building APIs...”
  - Good: “Backend: FastAPI (v0.100+)”
- Coding standards: reference standard tooling.
  - Bad: 5 pages of indentation rules.
  - Good: “Linting: `ruff`. Formatting: `black`. Type checking: `mypy --strict`.”

Rule 4.2: local vs. enterprise security
- Context matters.
- Localhost tool: focus on input validation and file-permission safety. Do not mention SOC 2, HIPAA, or rotating encryption keys unless relevant.
- Public SaaS: full security specs are required.

Rule 4.3: architecture over implementation
- Describe data flow, component boundaries, and state management.
- Do not write pseudo-code for every function.

## 5. The “SKIP” mandate

Rule 5.1: absolute adherence
- If you decide a stage (UX, market research, DevOps, etc.) is not needed, create a `SKIP.md` file.
- Stop there. Do not create any other files in that directory.
- Do not skip the folder but then write content “just in case.”

## Summary checklist for AI

Before generating content, ask:
1. Is this needed? (Or can I skip it?)
2. Is this appropriate for the scale? (simple tool vs enterprise system)
3. Does the user already know this? (Expert audience)
4. Am I hallucinating business value? (Open source vs commercial)
