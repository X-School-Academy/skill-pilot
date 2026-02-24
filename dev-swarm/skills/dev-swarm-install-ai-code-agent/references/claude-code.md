# claude-code Installation

Anthropic's Claude CLI tool for AI-assisted coding.

## Installation Methods

### macOS, Linux, WSL

**Option 1: npm (requires Node.js 18+)**
```bash
npm install -g @anthropic-ai/claude-code
```

**Option 2: Install Script**
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

**Option 3: Homebrew**
```bash
brew install --cask claude-code
```

### Windows PowerShell

```powershell
irm https://claude.ai/install.ps1 | iex
```

### Windows CMD

```cmd
curl -fsSL https://claude.ai/install.cmd -o install.cmd && install.cmd && del install.cmd
```

## Launching

```bash
claude
```

## Verification

```bash
claude --version
```

## First-Time Setup

1. Run `claude` in your terminal
2. Follow the authentication prompts
3. Sign in with your Anthropic account

## Documentation

- Official docs: https://docs.anthropic.com/claude-code
