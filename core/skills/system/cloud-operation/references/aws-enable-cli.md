# AWS — Enable CLI & MCP

Set up AWS credentials, save them to `config/.env`, and activate the `aws-api` MCP skill so AWS operations can be performed without manual Console interaction.

Default behavior: execute each step automatically where possible. Ask the user only when a step requires human verification, a site blocks automation, or account-specific confirmation is needed.

## When to Use

- AWS credentials are not yet in `config/.env`
- `aws-api` MCP skill is disabled or not synced
- Any task that requires programmatic AWS access

## Skip Condition

Use skill `key-safe` to get `AWS_ACCESS_KEY_ID` and `AWS_REGION`.

If both are non-empty, ask user whether to keep or replace them — replacing live credentials is an important confirmation.

In yolo mode, skip this check and create a new key using default values.

## Instructions

### Step 1: Check existing credentials

Use skill `key-safe` to get `AWS_ACCESS_KEY_ID` and `AWS_REGION`.

If both are set and user confirms to keep them, skip to Step 6 (sync only).

### Step 2: Warn user about external site

> **Security notice:** About to open aws.amazon.com. Confirm this is the official AWS website before entering any credentials.

Stop if the site appears untrusted or blocked.

### Step 3: AWS account sign-in

Open `https://aws.amazon.com/` via `agent-browser` skill:

- Signed in: proceed to Step 4.
- Not signed in: navigate to sign-in; ask user to complete only if CAPTCHA or MFA is required.
- No account: guide to sign-up page and explain free tier.

### Step 4: Create IAM access key

Navigate to IAM → Users → select user → **Security credentials** → **Create access key**:

1. Use case: **Command Line Interface (CLI)**
2. Copy **Access Key ID** and **Secret Access Key** (shown only once)

Ask user for help only if the Console blocks automated interaction or the correct IAM user cannot be inferred.

In yolo mode, always create a new access key.

### Step 5: Select AWS region

Use the region the user specified, or ask: "Which AWS region do you want to use?"

Default: **`ap-southeast-2`** (Sydney, AU)

Common options:
- `us-east-1` — N. Virginia
- `eu-west-1` — Ireland
- `ap-southeast-2` — Sydney (default)

In yolo mode, use the default without asking.

### Step 6: Save credentials

Use skill `key-safe` to save:

```
AWS_ACCESS_KEY_ID=<access-key-id>
AWS_SECRET_ACCESS_KEY=<secret-access-key>
AWS_REGION=<region>
DISABLE_AWS_API_MCP_SERVER=false
```

### Step 7: Sync MCP

```bash
core/bin/sync-mcp
core/bin/skill-install
```

### Step 8: Report result

```
AWS credentials:  saved to config/.env (keys not shown)
AWS region:       <region>
aws-api MCP:      enabled and synced
```
