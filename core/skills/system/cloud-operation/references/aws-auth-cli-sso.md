# AWS Auth - CLI SSO Login

Use AWS CLI SSO login when the user authenticates through AWS IAM Identity Center / SSO.

AWS CLI is used only for authentication setup and verification. After authentication is configured, use the `aws-api` MCP agent skill for AWS operations.

## Prerequisite

Follow [aws-cli-install.md](aws-cli-install.md) to confirm AWS CLI v2 is installed.

## Configure SSO Profile

For a new SSO profile:

```bash
aws configure sso --profile my-sso-profile
```

Ask the user for account-specific values when prompted, including the SSO start URL, SSO region, AWS account, permission set/role, default region, and output format.

Login:

```bash
aws sso login --profile my-sso-profile
```

Verify:

```bash
aws sts get-caller-identity --profile my-sso-profile
```

## Configure MCP Environment

Use skill `key-safe-sudo` to save empty long-term keys, enable MCP, and point MCP at the SSO profile:

```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_API_MCP_PROFILE_NAME=my-sso-profile
DISABLE_AWS_API_MCP_SERVER=false
```

Set `AWS_REGION` only when the user wants the MCP server to force a region. Otherwise use the SSO profile's configured region.

## Finalize

Return to [aws-enable-cli.md](aws-enable-cli.md) and complete **Finalize: Sync MCP** and **Finalize: Report Result**.
