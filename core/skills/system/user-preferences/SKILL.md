---
name: user-preferences
description: Capture and apply user corrections, preferences, and workflow instructions. Use when the user asks to use a different agent skill or tool, says to handle tasks this way in the future, wants to avoid a repeated mistake, or explicitly corrects how future tasks should be handled.
---

# AI Builder - User Preferences

Capture user corrections and turn them into persistent working rules for future tasks.

## When to Use This Skill

- The user corrects a previous action
- The user says "please use X", "do not use Y", or "next time do Z"
- The user says to do something this way in the future
- The user rejects a tool choice and specifies the preferred one
- The user adds a standing workflow rule that should be remembered

## Your Roles in This Skill

- **Project Manager**: Identify whether the user statement is a durable preference or a one-off request
- **Backend Developer**: Update the persistent preference record accurately and minimally
- **Technical Writer**: Rewrite the preference into a short, reusable rule without losing meaning

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

### Step 1: Detect a corrective preference

- Look for user phrases that correct your prior behavior or specify a preferred future behavior
- Treat direct corrections as high priority, including:
  - "please use ..."
  - "do not use ..."
  - "next time ..."
  - "in the future, please ..."
  - "please do this in the future ..."
  - "you should ..."
  - "No, use ..."
- If the user is only making a one-time request for the current task and does not imply future reuse, do not record it unless they ask

### Step 2: Apply the correction immediately

- Change your current action to follow the user correction in the same turn whenever feasible
- Do not defend the prior choice if the new instruction is valid and lower risk
- If the correction conflicts with safety, sandbox, or project constraints, explain the constraint and record the preference with that limitation

### Step 3: Record the preference in `dev-swarm/user_preferences.md`

- Update `dev-swarm/user_preferences.md` whenever the user gives a durable corrective preference
- Write the rule as a short actionable bullet
- Keep the wording generic enough to help in future tasks, but specific enough to prevent the same mistake
- Preserve existing preferences and append or refine instead of rewriting unrelated lines

### Step 4: Record tool and skill preferences explicitly

- If the user says a specific agent skill or tool should be used, record that preference clearly
- Example:
  - If the user says "please use agent skill git commit", record a rule stating that git commits should use the relevant agent skill when available
- If the user says not to use a technique, record that too

### Step 5: Keep the file concise and practical

- Prefer one bullet per durable rule
- Avoid long explanations, history, or blame
- Do not record transient details that are unlikely to matter again

### Step 6: Confirm the change briefly

- After updating the file, tell the user the preference has been recorded
- Mention the affected file path

## Expected Output

- The current task behavior corrected to match the user's instruction
- A concise new or updated rule in `dev-swarm/user_preferences.md`
- A short confirmation to the user

## Key Principles

- Correct the action first
- Record only durable preferences
- Keep preference rules short and reusable
- Prefer explicit tool and skill guidance when the user provides it

## Common Issues

- Over-recording one-off requests:
  only save durable workflow preferences
- Vague wording:
  rewrite the user correction into a direct actionable rule
- Repeating the same mistake:
  check `dev-swarm/user_preferences.md` early in future tasks and follow it
