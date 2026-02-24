
## ai_providers.json5 keys

For each `llm` provider config, you can define:

- `sandbox-args`: array of CLI args used when `sandbox_mode=true`
- `auto-args`: array of CLI args used when `auto_allow=true`
- `network-args`: array of CLI args used when `network_allow=true`

Current WebUI/frontend default runtime values:

- `auto_allow=false`
- `network_allow=false`
- `sandbox_mode=true`

Claude uses `webui/claude-sandbox-settings.json` through `sandbox-args`.

## codex

https://developers.openai.com/codex/security/
```bash
codex --sandbox workspace-write --ask-for-approval never 
```

The workspace includes the current directory and temporary directories


For the Codex app, CLI, or IDE Extension, the default workspace-write sandbox mode keeps network access turned off unless you enable it in your configuration in config.toml:

[sandbox_workspace_write]
network_access = true

```bash
codex --sandbox workspace-write --ask-for-approval never \
  --config sandbox_workspace_write.network_access=true
```

## gemini

https://geminicli.com/docs/cli/sandbox/

```bash
# Enable sandboxing with command flag: -s or --sandbox
gemini -s -p "analyze the code structure"

# Use environment variable
export GEMINI_SANDBOX=true
gemini -p "run the test suite"

  -y, --yolo                      Automatically accept all actions (aka YOLO mode, see https://www.youtube.com/watch?v=xvFZjo5PgG0 for more details)?  [boolean] [default: false]
      --approval-mode             Set the approval mode: default (prompt for approval), auto_edit (auto-approve edit tools), yolo (auto-approve all tools), plan (read-only mode)  [string] [choices: "default", "auto_edit", "yolo", "plan"]

```

# Configure in settings.json
```json
{
  "tools": {
    "sandbox": "docker"
  }
}
```

The attempt to create /tmp/123.txt failed with "Operation not permitted," which is likely due to macOS Seatbelt restrictions preventing
  access to paths outside the project or its designated temporary directory. You may need to adjust your Seatbelt profile to allow this, or
  I can create the file within the project's temporary directory instead:
  ~/.gemini/tmp/3023e9e2dabbaa3d4ae46e9a8a9eb6c28fe9b3f9bec73ddae831d310cec456ae/123.txt. Would you like me to do that?

* WebFetch working in sandbox mode


## claude

https://code.claude.com/docs/en/sandboxing

Network access is controlled through a proxy server running outside the sandbox: Domain restrictions: Only approved domains can be accessed

You can enable sandboxing by running the /sandbox command - and configured via settings, and the CLI flag list doesn’t include --sandbox.

Customize sandbox behavior through your settings.json file

claude --dangerously-skip-permissions

/sandbox

Configure Mode:
 ❯ 1. Sandbox BashTool, with auto-allow (current)  
   2. Sandbox BashTool, with regular permissions 
   3. No Sandbox 

 Auto-allow mode: Commands will try to run in the sandbox automatically, and attempts to run outside of the sandbox fallback to regular permissions. Explicit ask/deny rules are always respected.   

claude -p --settings ./webui/claude-sandbox-settings.json

```json
{
  "sandbox": {
    "enabled": true,
    "autoAllowBashIfSandboxed": true,
    "allowUnsandboxedCommands": false,
    "network": {
      "allowedDomains": ["github.com", "*.npmjs.org"]
    }
  }
}
```

## opencode

JSON mode in cli

```json
{
    "id": "opencode",
    "name": "OpenCode CLI",
    "bin": "opencode",
    "args": ["--format", "json", "run", "{{prompt}}"]
}
```

OpenCode does not sandbox the agent. The permission system exists as a UX feature to help users stay aware of what actions the agent is taking - it prompts for confirmation before executing commands, writing files, etc. However, it is not designed to provide security isolation.

If you need true isolation, run OpenCode inside a Docker container or VM.

YOLO Mode: you can just set your permissions to below, this overrides everything. has to be the opencode.json in the repo because its takes priority, not the the global config (~/.config/opencode/config.json)

```json
{
  "permission": {
    "*": {
      "*": "allow",
    }
  }
}
```


## Open source - The sandbox runtime for AI agent

https://github.com/anthropic-experimental/sandbox-runtime


