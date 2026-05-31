# AWS Auth - Long-Term Credentials

Use long-term credentials when the user explicitly chooses the existing access-key solution or cannot use AWS CLI managed authentication.

## Check Existing Credentials

Use skill `keys-safe-guard` to get `AWS_ACCESS_KEY_ID` and `AWS_REGION`.

If both are set and the user confirms keeping them, skip to **Finalize**.

## AWS Account Sign-In

Open `https://aws.amazon.com/` via `agent-browser` skill after the user confirms the site is trusted:

- Signed in: proceed to create an IAM access key.
- Not signed in: navigate to sign-in; ask user to complete only if CAPTCHA or MFA is required.
- No account: guide to sign-up page and explain free tier.

## Create IAM Access Key

Navigate to IAM -> Users -> select user -> **Security credentials** -> **Create access key**:

1. Use case: **Command Line Interface (CLI)**
2. Copy **Access Key ID** and **Secret Access Key**. The secret is shown only once.

Ask user for help only if the Console blocks automated interaction or the correct IAM user cannot be inferred.

In yolo mode, always create a new access key.

## Select AWS Region

Use the region the user specified, or ask:

> Which AWS region do you want to use?

Default: **`ap-southeast-2`** (Sydney, AU)

Common options:

- `us-east-1` - N. Virginia
- `eu-west-1` - Ireland
- `ap-southeast-2` - Sydney (default)

In yolo mode, use the default without asking.

## Save Credentials

Use skill `keys-safe-guard` to save:

```
AWS_ACCESS_KEY_ID=<access-key-id>
AWS_SECRET_ACCESS_KEY=<secret-access-key>
AWS_REGION=<region>
AWS_API_MCP_PROFILE_NAME=
DISABLE_AWS_API_MCP_SERVER=false
```

## Finalize

Return to [aws-enable-cli.md](aws-enable-cli.md) and complete **Finalize: Sync MCP** and **Finalize: Report Result**.
