# Reverse-Engineering Missing Docs

## Goal

Extract a simple, general understanding of the product, then reconstruct stages, sprints/backlogs, and feature specs.

## Step 1: Capture the Simple/General Idea

1. Scan for any existing hints:
   - `README*`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `Makefile`
   - App entry points, UI shells, or API routers
2. Summarize in 3-5 bullets:
   - What the product is
   - Who it serves
   - Core workflows or jobs-to-be-done
   - Key constraints or dependencies
3. Draft/refresh `ideas.md` with the summary.

## Step 2: Reconstruct Stage Artifacts

Rebuild the stage folders based on the codebase reality:

- `00-init-ideas/`: Translate the simple idea into a problem statement and goals.
- `01-market-research/`: Note any implied competitors or market constraints from the code domain.
- `02-personas/`: Infer likely user types from features and terminology.
- `03-mvp/`: Identify the smallest workable product slice that the code already supports.
- `04-prd/`: Document functional and non-functional behaviors visible in the code.
- `05-ux/`: Map UI flows or API workflows discovered.
- `06-architecture/`: Diagram or describe system structure from repo layout.
- `07-tech-specs/`: Capture languages, frameworks, infra hints.
- `08-devops/`: Note CI/CD or deployment scripts.
- `10-sprints/`: Create sprints/backlogs based on current features and gaps.
- `11-deployment/`: Document current deployment expectations from config files.

Use brief, factual notes; avoid speculation unless clearly marked.

## Step 3: Rebuild Sprints and Backlogs

1. Extract features from the codebase (routes, UI screens, services).
2. Group them into epics and backlogs in `10-sprints/`.
3. Flag missing or partial implementations as backlog items.

## Step 4: Populate the Features Folder

1. Create or update feature specs under `features/` using consistent naming.
2. Each feature should include:
   - Problem statement
   - User story
   - Acceptance criteria
   - Relevant code references

## Step 5: Review With the User

Summarize the reconstructed artifacts and ask for corrections before proceeding.
