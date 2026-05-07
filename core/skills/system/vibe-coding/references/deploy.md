# Stage Reference: deploy

Deploy a Vibe Coding project to the user's chosen production environment.

## When to Use

- The user asks to deploy the project
- Implementation is ready for deployment
- The project needs a production release

## Steps

### Step 1: Read the Implementation Context

Read `design-docs/implement.md` and identify deployment target, runtime, and dependencies.

### Step 2: Determine the Deployment Target

If no deployment target is specified in `requirements.md`, `plan.md`, or `implement.md`, ask the user how and where to deploy before proceeding.

### Step 3: Prepare and Deploy

Confirm app start command, environment requirements, exposed ports, and release steps. Use the appropriate tools for the chosen target. Do not assume credentials or infrastructure already exist.

### Step 4: Update the Deployment Record

Write `design-docs/deployment.md` (overwrite — it is a living doc):

- What was deployed
- Where it was deployed
- Environment / runtime details
- Remaining setup items

### Step 5: Report

Summarize the outcome and next steps.
