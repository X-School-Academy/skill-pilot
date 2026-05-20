# AWS Auth - CLI Website Login

Use AWS CLI website login when the user wants browser-based AWS authentication with short-term cached credentials.

AWS CLI is used only for authentication setup and verification. After authentication is configured, use the `aws-api` MCP agent skill for AWS operations.

## Prerequisite

Follow [aws-cli-install.md](aws-cli-install.md) to confirm AWS CLI is installed and new enough for `aws login`.

## Login

For the default profile:

```bash
aws login
```

For a named profile:

```bash
aws login --profile my-dev-profile
```

If the browser cannot open on the current device, use remote login:

```bash
aws login --remote
```

AWS CLI will print a URL and code. Ask the user to complete the browser login if needed.

After login, verify the CLI-authenticated identity:

```bash
aws sts get-caller-identity
```

Useful profile checks:

```bash
aws configure list-profiles
aws configure list
```

Logout commands, if needed:

```bash
aws logout
aws logout --profile my-dev-profile
aws logout --all
```

AWS CLI caches temporary login credentials under `~/.aws/login/cache` on Linux and macOS. To change that cache location, set `AWS_LOGIN_CACHE_DIRECTORY`.

## Configure MCP Environment

Use skill `key-safe-sudo` to save empty long-term keys and enable MCP:

```
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
DISABLE_AWS_API_MCP_SERVER=false
```

Set `AWS_API_MCP_PROFILE_NAME` only when the user chose a non-default AWS CLI profile:

```
AWS_API_MCP_PROFILE_NAME=<profile-name>
```

If the user uses the default AWS CLI profile, leave `AWS_API_MCP_PROFILE_NAME` empty or unset so boto3 follows the default credential chain.

Set `AWS_REGION` only when the user wants the MCP server to force a region:

```
AWS_REGION=<region>
```

If no explicit region is needed, leave `AWS_REGION` empty or unset and use the AWS CLI profile's default region.

## Finalize

Return to [aws-enable-cli.md](aws-enable-cli.md) and complete **Finalize: Sync MCP** and **Finalize: Report Result**.
