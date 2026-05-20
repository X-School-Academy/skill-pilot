# AWS CLI Install

Install or update AWS CLI when an AWS CLI authentication method requires it.

## When to Use

- The user chose AWS CLI website login
- The user chose AWS CLI SSO login
- `aws` is missing
- The installed AWS CLI version is too old for the requested authentication method

## Check AWS CLI

Check whether AWS CLI is installed:

```bash
command -v aws
aws --version
```

For `aws login`, required version is **AWS CLI v2.34.50 or newer**.

For `aws sso login`, AWS CLI v2 is required. Prefer updating to the latest available AWS CLI v2 if the installed version is old or authentication fails.

Ask before installing or updating AWS CLI.

## Install or Update on macOS

```bash
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /
```

The package installs files to `/usr/local/aws-cli` and creates a symlink in `/usr/local/bin`.

## Install or Update on Linux x86_64

```bash
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install --bin-dir /usr/local/bin --install-dir /usr/local/aws-cli --update
```

For Linux arm64, use `awscli-exe-linux-aarch64.zip` instead of `awscli-exe-linux-x86_64.zip`.

If the Linux distro has snap installed:

```bash
sudo snap install aws-cli --classic
```

## Verify Install

```bash
aws --version
```

Continue to the selected authentication method after AWS CLI is available.
