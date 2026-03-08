---
name: enable-aws-cli
description: Set up AWS credentials and enable the aws-api MCP skill. Guides user through AWS sign-in, IAM access key creation, and region selection. Saves keys to .env and syncs MCP. Skip if already configured. Use for any task that needs AWS API access.
---

# Enable AWS CLI API Skills

Guide the user to obtain AWS credentials, save them securely to `config/.env`, and activate the
`aws-api` MCP skill so AWS operations can be performed without manual Console interaction.

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

If both are non-empty, ask user whether to skip or replace them.

## Instructions

### Step 1: Check existing credentials

Use skill `key-safe` to get `AWS_ACCESS_KEY_ID` and `AWS_REGION`.

If both are set and user confirms to keep them, skip to Step 6 (sync only).

### Step 2: Warn user about external site

> **Security notice:** About to open aws.amazon.com. Confirm this is the official AWS website before entering any credentials.

### Step 3: AWS account sign-in or creation

Open `https://aws.amazon.com/` via `playwright-cli`:

```
playwright-cli open https://aws.amazon.com/ --extension --headed
```

- Signed in: proceed to Step 4.
- Not signed in: ask user to sign in.
- No account: guide user to sign-up page. Explain free tier (750 hrs/month for eligible instances; credit card required but no charge under free limits).

### Step 4: Create IAM access key

Navigate to IAM → Users → select user → **Security credentials** → **Create access key**:
1. Use case: **Command Line Interface (CLI)**
2. Copy **Access Key ID** and **Secret Access Key** (shown only once)

Ask user to paste both values privately.

### Step 5: Select AWS region

Ask: "Which AWS region do you want to use?"

Default: **`ap-southeast-2`** (Sydney, AU)

Common options if user is unsure:
- `us-east-1` — N. Virginia
- `eu-west-1` — Ireland
- `ap-southeast-2` — Sydney ← default

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

## Output

Plain text result shown to user:

```
AWS credentials:  saved to config/.env (keys not shown)
AWS region:       <region>
aws-api MCP:      enabled and synced
```

## Common Issues

- **Root account keys**: prefer IAM user keys — note this but proceed if user chooses root
- **sync-mcp fails**: verify `DISABLE_AWS_API_MCP_SERVER=false` was written to `.env`
- **skill-install not found**: run `ls core/bin/` to confirm the binary exists
