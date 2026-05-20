# AWS Auth - CLI SSO Login

Use AWS CLI SSO login when the user authenticates through AWS IAM Identity Center / SSO.

AWS CLI is used only for authentication setup and verification. After authentication is configured, use the `aws-api` MCP agent skill for AWS operations.

## Prerequisite

Follow [aws-cli-install.md](aws-cli-install.md) to confirm AWS CLI v2 is installed.

## Get SSO Start URL

If the user does not already know the SSO start URL (AWS access portal URL), use the `agent-browser` skill to retrieve it from the AWS Console after the user confirms `https://console.aws.amazon.com/` is trusted:

1. Open `https://console.aws.amazon.com/singlesignon/` (IAM Identity Center). Ask the user to complete sign-in only if CAPTCHA or MFA is required.
2. Make sure the Console region matches the region where IAM Identity Center is enabled (shown in the top-right region selector).
3. On the **Dashboard**, read the **Settings summary** panel and copy the **AWS access portal URL** (format: `https://<id>.awsapps.com/start`).
4. Note the **Region** displayed in the same panel; this is the SSO region to use when configuring the profile.

If IAM Identity Center is not yet enabled, ask the user to approve enabling it. On approval, proceed with the Console flow to enable IAM Identity Center (the user may need to complete steps that require MFA or organization-level consent). If the user declines, fall back to [aws-auth-long-term-token.md](aws-auth-long-term-token.md).

## Configure SSO Profile

For a new SSO profile:

```bash
aws configure sso --profile my-sso-profile
```

Provide the SSO start URL and SSO region from the previous step. Ask the user for the remaining account-specific values when prompted: AWS account, permission set/role, default region, and output format.

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
