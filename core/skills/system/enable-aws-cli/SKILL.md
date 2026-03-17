---
name: enable-aws-cli
description: Set up AWS credentials and enable the aws-api MCP skill. Execute the flow automatically where possible, ask the user only for human verification or critical confirmations, save credentials to .env, and sync MCP. In yolo mode, always use default values and create a new key.
---

# Enable AWS CLI API Skills

Guide the user to obtain AWS credentials, save them securely to `config/.env`, and activate the
`aws-api` MCP skill so AWS operations can be performed without manual Console interaction.

Default behavior: execute each step automatically whenever the AI can do so safely. Only ask the user for help when a step requires human verification, the website blocks automation, or important account-specific information needs explicit user confirmation.

## When to Use This Skill

- AWS credentials are not yet in `config/.env`
- `aws-api` MCP skill is disabled or not synced
- Any task that requires programmatic AWS access

## Your Roles in This Skill

- **SysOps Engineer**: Configure AWS credentials and activate MCP tooling
- **Security Engineer**: Ensure credentials are stored only through skill `key-safe`

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

## Preconditions

None — this skill is self-contained.

## Workflow Usage Requirement

When this skill is used in a workflow agent node:

- Output result as plain text. If the user asked to save it to a file, write it there.
- Include concise context in the output (credentials status, selected region, and MCP sync status) so downstream agents can safely continue.

## Skip Condition

Check if credentials are already configured:

- Use skill `key-safe` to get `AWS_ACCESS_KEY_ID` and `AWS_REGION`.

If both are non-empty, ask user whether to keep or replace them because replacing live AWS credentials is an important confirmation.

In yolo mode, do not stop here for preference collection. Use the default region and create a new access key unless a hard blocker requires user help.

## Instructions

### Step 1: Check existing credentials

Use skill `key-safe` to get `AWS_ACCESS_KEY_ID` and `AWS_REGION`.

If both are set and user confirms to keep them, skip to Step 6 (sync only).

### Step 2: Warn user about external site

> **Security notice:** About to open aws.amazon.com. Confirm this is the official AWS website before entering any credentials.

If the site appears untrusted, unexpected, or blocked by login challenges, stop and ask the user to verify the page before continuing.

### Step 3: AWS account sign-in or creation

Open `https://aws.amazon.com/` via `playwright-cli agent skill`:

```
playwright-cli open https://aws.amazon.com/ --extension --headed
```

- Signed in: proceed to Step 4.
- Not signed in: attempt to navigate to sign-in automatically, then ask user to complete sign-in only if credentials, MFA, CAPTCHA, or other human checks are required.
- No account: guide user to sign-up page. Explain free tier (750 hrs/month for eligible instances; credit card required but no charge under free limits).

Do not ask the user to drive normal page navigation if the AI can continue safely.

### Step 4: Create IAM access key

Navigate to IAM → Users → select user → **Security credentials** → **Create access key**:
1. Use case: **Command Line Interface (CLI)**
2. Copy **Access Key ID** and **Secret Access Key** (shown only once)

The AI should perform this flow directly when the Console session is accessible.

Ask the user for help only if:
- the Console requires a human-only verification step,
- the correct IAM user cannot be inferred safely,
- the site blocks automated interaction.

In yolo mode, always create a new access key instead of reusing or asking whether to reuse an existing one.

### Step 5: Select AWS region

If the user already specified a region, use it.

Otherwise ask: "Which AWS region do you want to use?"

Default: **`ap-southeast-2`** (Sydney, AU)

Common options if user is unsure:
- `us-east-1` — N. Virginia
- `eu-west-1` — Ireland
- `ap-southeast-2` — Sydney ← default

In yolo mode, do not ask. Use the default region `ap-southeast-2`.

### Step 6: Save credentials to .env — one password prompt

Use skill `key-safe` to save:
- `AWS_ACCESS_KEY_ID=<access-key-id>`
- `AWS_SECRET_ACCESS_KEY=<secret-access-key>`
- `AWS_REGION=<region>`
- `DISABLE_AWS_API_MCP_SERVER=false`

### Step 7: Sync MCP and install aws-api skill

```bash
core/bin/sync-mcp
core/bin/skill-install
```

### Step 8: Report result

Output result as plain text. If the user asked to save it to a file, write it there.

Include whether the flow was fully automated or whether user help was required for sign-in, verification, or confirmation.

## Output

Plain text result shown to user:

```
AWS credentials:  saved to config/.env (keys not shown)
AWS region:       <region>
aws-api MCP:      enabled and synced
```

