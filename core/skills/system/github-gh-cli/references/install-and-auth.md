# Install and Auth

Use this reference when `gh` is missing, when authentication is not configured, or when the user explicitly asks to set up GitHub CLI.

## 1. Readiness checks

Check installation:

```bash
command -v gh
gh --version
```

Check authentication:

```bash
gh auth status
```

Treat authentication as missing if `gh auth status` reports that GitHub.com is not logged in.

## 2. Installation

If `gh` is unavailable, install it with:

```bash
brew install gh
```

If the user asked for automatic execution, run the install directly. Otherwise, tell the user you are about to install GitHub CLI with Homebrew and ask for confirmation first.

## 3. Interactive auth session

Run `gh auth login` inside a tmux-backed terminal session rather than a one-shot shell command because the login flow is interactive.

Preferred session pattern:

- Use the `terminal-open-session` skill or equivalent tmux-backed terminal session
- Start a shell in the repository root
- Run `gh auth login`

## 4. Default prompt answers

When the user asked for automatic execution, accept the default choices below without pausing.

Interactive answers:

- `Where do you use GitHub?` -> `GitHub.com`
- `What is your preferred protocol for Git operations on this host?` -> `SSH`
- `Upload your SSH public key to your GitHub account?` -> `Skip`
- `How would you like to authenticate GitHub CLI?` -> `Login with a web browser`

Expected flow:

```text
gh auth login
? Where do you use GitHub? GitHub.com
? What is your preferred protocol for Git operations on this host? SSH
? Upload your SSH public key to your GitHub account? Skip
? How would you like to authenticate GitHub CLI? Login with a web browser

! First copy your one-time code: XXXX-XXXX
Press Enter to open https://github.com/login/device in your browser...
✓ Authentication complete.
- gh config set -h github.com git_protocol ssh
✓ Configured git protocol
✓ Logged in as <username>
```

If the user did not ask for automatic execution, present those defaults first and ask the user to confirm before continuing.

## 5. Browser step

Before opening the device-login URL, warn the user:

- You are about to open a remote website
- They should confirm it is the official GitHub domain
- They should not enter secrets into an unexpected or suspicious page

Then choose one of these paths:

- Use the web browser agent skill to open `https://github.com/login/device`
- If the user prefers another browser, give them the URL and one-time code and let them complete the step manually

Do not force a browser choice when the user explicitly prefers a different one.

## 6. Post-login checks

After login, confirm:

```bash
gh auth status
gh config get git_protocol -h github.com
```

Expected result:

- Authenticated for `github.com`
- Git protocol is `ssh`

## 7. Failure handling

- If Homebrew is unavailable, report that blocker and stop rather than guessing another installer unless the user asks
- If device login fails, rerun `gh auth login` and provide the new code and URL
- If the browser step is blocked, let the user complete the URL manually and keep monitoring the tmux session
- If `gh auth status` still fails after login, report the exact failure and stop for user guidance
