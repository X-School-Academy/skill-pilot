# Authentication Patterns

Login flows, session persistence, OAuth, 2FA, and authenticated browsing.

**Related**: [session-management.md](session-management.md) for state persistence details, [SKILL.md](../SKILL.md) for quick start.

## Contents

- [Import Auth from Your Browser](#import-auth-from-your-browser)
- [Persistent Profiles](#persistent-profiles)
- [Session Persistence](#session-persistence)
- [Basic Login Flow](#basic-login-flow)
- [Saving Authentication State](#saving-authentication-state)
- [Restoring Authentication](#restoring-authentication)
- [OAuth / SSO Flows](#oauth--sso-flows)
- [Two-Factor Authentication](#two-factor-authentication)
- [HTTP Basic Auth](#http-basic-auth)
- [Cookie-Based Auth](#cookie-based-auth)
- [Token Refresh Handling](#token-refresh-handling)
- [Security Best Practices](#security-best-practices)

## Import Auth from Your Browser

The fastest way to authenticate is to reuse cookies from a Chrome session you are already logged into.

**Step 1: Enable Chrome remote debugging**

Refer to [init.md](init.md) for the platform command to open `chrome://inspect/#remote-debugging`, then ask the user to enable remote debugging in Chrome.

Log in to your target site(s) in that Chrome window as you normally would.

**Step 2: Grab the auth state**

```bash
# Auto-discover the running Chrome and save its cookies + localStorage
core/bin/agent-browser --auto-connect state save ./my-auth.json
```

**Step 3: Reuse in automation**

```bash
# Load auth at launch
core/bin/agent-browser --state ./my-auth.json open https://app.example.com/dashboard

# Or load into an existing session
core/bin/agent-browser state load ./my-auth.json
core/bin/agent-browser open https://app.example.com/dashboard
```

This works for any site, including those with complex OAuth flows, SSO, or 2FA -- as long as Chrome already has valid session cookies.

> **Security note:** State files contain session tokens in plaintext. Add them to `.gitignore`, delete when no longer needed, and set `AGENT_BROWSER_ENCRYPTION_KEY` for encryption at rest. See [Security Best Practices](#security-best-practices).

**Tip:** Combine with `--session-name` so the imported auth auto-persists across restarts:

```bash
core/bin/agent-browser --session-name myapp state load ./my-auth.json
# From now on, state is auto-saved/restored for "myapp"
```

## Persistent Profiles

Use `--profile` to point agent-browser at a Chrome user data directory. This persists everything (cookies, IndexedDB, service workers, cache) across browser restarts without explicit save/load:

```bash
# First run: login once
core/bin/agent-browser --profile ~/.myapp-profile open https://app.example.com/login
# ... complete login flow ...

# All subsequent runs: already authenticated
core/bin/agent-browser --profile ~/.myapp-profile open https://app.example.com/dashboard
```

Use different paths for different projects or test users:

```bash
core/bin/agent-browser --profile ~/.profiles/admin open https://app.example.com
core/bin/agent-browser --profile ~/.profiles/viewer open https://app.example.com
```

Or set via environment variable:

```bash
export AGENT_BROWSER_PROFILE=~/.myapp-profile
core/bin/agent-browser open https://app.example.com/dashboard
```

## Session Persistence

Use `--session-name` to auto-save and restore cookies + localStorage by name, without managing files:

```bash
# Auto-saves state on close, auto-restores on next launch
core/bin/agent-browser --session-name twitter open https://twitter.com
# ... login flow ...
core/bin/agent-browser close  # state saved to ~/.agent-browser/sessions/

# Next time: state is automatically restored
core/bin/agent-browser --session-name twitter open https://twitter.com
```

Encrypt state at rest:

```bash
export AGENT_BROWSER_ENCRYPTION_KEY=$(openssl rand -hex 32)
core/bin/agent-browser --session-name secure open https://app.example.com
```

## Basic Login Flow

```bash
# Navigate to login page
core/bin/agent-browser open https://app.example.com/login
core/bin/agent-browser wait --load networkidle

# Get form elements
core/bin/agent-browser snapshot -i
# Output: @e1 [input type="email"], @e2 [input type="password"], @e3 [button] "Sign In"

# Fill credentials
core/bin/agent-browser fill @e1 "user@example.com"
core/bin/agent-browser fill @e2 "password123"

# Submit
core/bin/agent-browser click @e3
core/bin/agent-browser wait --load networkidle

# Verify login succeeded
core/bin/agent-browser get url  # Should be dashboard, not login
```

## Saving Authentication State

After logging in, save state for reuse:

```bash
# Login first (see above)
core/bin/agent-browser open https://app.example.com/login
core/bin/agent-browser snapshot -i
core/bin/agent-browser fill @e1 "user@example.com"
core/bin/agent-browser fill @e2 "password123"
core/bin/agent-browser click @e3
core/bin/agent-browser wait --url "**/dashboard"

# Save authenticated state
core/bin/agent-browser state save ./auth-state.json
```

## Restoring Authentication

Skip login by loading saved state:

```bash
# Load saved auth state
core/bin/agent-browser state load ./auth-state.json

# Navigate directly to protected page
core/bin/agent-browser open https://app.example.com/dashboard

# Verify authenticated
core/bin/agent-browser snapshot -i
```

## OAuth / SSO Flows

For OAuth redirects:

```bash
# Start OAuth flow
core/bin/agent-browser open https://app.example.com/auth/google

# Handle redirects automatically
core/bin/agent-browser wait --url "**/accounts.google.com**"
core/bin/agent-browser snapshot -i

# Fill Google credentials
core/bin/agent-browser fill @e1 "user@gmail.com"
core/bin/agent-browser click @e2  # Next button
core/bin/agent-browser wait 2000
core/bin/agent-browser snapshot -i
core/bin/agent-browser fill @e3 "password"
core/bin/agent-browser click @e4  # Sign in

# Wait for redirect back
core/bin/agent-browser wait --url "**/app.example.com**"
core/bin/agent-browser state save ./oauth-state.json
```

## Two-Factor Authentication

Handle 2FA with manual intervention:

```bash
# Login with credentials
core/bin/agent-browser open https://app.example.com/login --headed  # Show browser
core/bin/agent-browser snapshot -i
core/bin/agent-browser fill @e1 "user@example.com"
core/bin/agent-browser fill @e2 "password123"
core/bin/agent-browser click @e3

# Wait for user to complete 2FA manually
echo "Complete 2FA in the browser window..."
core/bin/agent-browser wait --url "**/dashboard" --timeout 120000

# Save state after 2FA
core/bin/agent-browser state save ./2fa-state.json
```

## HTTP Basic Auth

For sites using HTTP Basic Authentication:

```bash
# Set credentials before navigation
core/bin/agent-browser set credentials username password

# Navigate to protected resource
core/bin/agent-browser open https://protected.example.com/api
```

## Cookie-Based Auth

Manually set authentication cookies:

```bash
# Set auth cookie
core/bin/agent-browser cookies set session_token "abc123xyz"

# Navigate to protected page
core/bin/agent-browser open https://app.example.com/dashboard
```

## Token Refresh Handling

For sessions with expiring tokens:

```bash
#!/bin/bash
# Wrapper that handles token refresh

STATE_FILE="./auth-state.json"

# Try loading existing state
if [[ -f "$STATE_FILE" ]]; then
    core/bin/agent-browser state load "$STATE_FILE"
    core/bin/agent-browser open https://app.example.com/dashboard

    # Check if session is still valid
    URL=$(core/bin/agent-browser get url)
    if [[ "$URL" == *"/login"* ]]; then
        echo "Session expired, re-authenticating..."
        # Perform fresh login
        core/bin/agent-browser snapshot -i
        core/bin/agent-browser fill @e1 "$USERNAME"
        core/bin/agent-browser fill @e2 "$PASSWORD"
        core/bin/agent-browser click @e3
        core/bin/agent-browser wait --url "**/dashboard"
        core/bin/agent-browser state save "$STATE_FILE"
    fi
else
    # First-time login
    core/bin/agent-browser open https://app.example.com/login
    # ... login flow ...
fi
```

## Security Best Practices

1. **Never commit state files** - They contain session tokens
   ```bash
   echo "*.auth-state.json" >> .gitignore
   ```

2. **Use environment variables for credentials**
   ```bash
   core/bin/agent-browser fill @e1 "$APP_USERNAME"
   core/bin/agent-browser fill @e2 "$APP_PASSWORD"
   ```

3. **Clean up after automation**
   ```bash
   core/bin/agent-browser cookies clear
   rm -f ./auth-state.json
   ```

4. **Use short-lived sessions for CI/CD**
   ```bash
   # Don't persist state in CI
   core/bin/agent-browser open https://app.example.com/login
   # ... login and perform actions ...
   core/bin/agent-browser close  # Session ends, nothing persisted
   ```
