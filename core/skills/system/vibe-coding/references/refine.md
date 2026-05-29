# Stage Reference: refine

Refine the trigger document for clarity, grammar, and logic without changing the requested scope. The target file depends on the active flow:

- New project flow: `requirements.md`
- Update flow: `update.md`
- Fix flow: `issues.md`

## When to Use

- The user wants to clean up the trigger document before planning
- The trigger file is rough or inconsistent
- The requirement may reference an existing repo, website, game, app, clone, port, remake, or reimplementation

## Steps

### Step 1: Identify the Active Flow and Read the Trigger File

- New project: read `requirements.md`
- Update: read `update.md`
- Fix: read `issues.md`

Identify wording, grammar, and logic issues.

### Step 2: Check for Reference-Project Work (new project flow only)

If the requirement asks to learn from, clone, port, remake, reimplement, or get inspiration from a source-code repo, live website, game, or app, follow `references/refine-reference-project.md`.

Otherwise continue with the normal refinement steps below.

### Step 3: Refine with Steps

1. Fix English, clarity, consistency, and obvious logic issues. Do not add new requirements, features, or constraints — only make the existing content clear and unambiguous. Ask the user to approve the refined content.

2. After approval, archive the original trigger file (move it under `design-archive/` with a timestamp suffix), then create a new file with the same trigger-file name and begin a design-specification interview:

   Interview the user relentlessly about every aspect of the requirement until you reach a shared understanding. For each question, provide your recommended answer.

   Ask the questions one at a time. Cover all of the following that are applicable:
   - Goals
   - User scenarios
   - Inputs and outputs
   - Business rules
   - Boundary conditions
   - Technical constraints
   - Acceptance criteria

   The goal is to evolve the document into a design specification before we make a development plan.

### Step 4: Save the Refined File

Write the improved content back to the same trigger file (living doc — no archive copy needed).

### Step 5: Summarize

Briefly report what was refined.
