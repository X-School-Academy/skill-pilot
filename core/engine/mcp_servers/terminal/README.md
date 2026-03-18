# Terminal MCP Server

A unified MCP server for terminal automation across:

- Local commands
- Remote SSH commands (`ssh:<profile>`)
- Long-running workloads via `tmux` (local or remote)

## Platform Compatibility

| Platform | Local Sessions | SSH to Linux | Notes |
|----------|---------------|--------------|-------|
| **Linux** | ✅ Full support | ✅ Full support | Native POSIX environment |
| **macOS** | ✅ Full support | ✅ Full support | Native POSIX environment |
| **Windows 10/11** | ❌ Not supported | ✅ **Works via Paramiko** | See [Windows Usage](#windows-usage) below |
| **WSL2 (Windows)** | ✅ Full support | ✅ Full support | **Recommended for Windows** - Full compatibility |

> **🪟 Windows Users Quick Start:**
> - **Need local PowerShell?** → Use WSL2 (full support)
> - **Only managing remote Linux servers?** → Native Windows works (SSH via Paramiko)
> - **Want everything?** → WSL2 is the best choice

### Windows Usage

**✅ What Works on Windows:**
- **Remote SSH connections to Linux servers** (via Paramiko)
  - All SSH operations: `exec_command`, `sudo_exec_command`, sessions, tmux
  - File transfers: `scp_upload`, `scp_download`
  - Port forwarding: tunnels work perfectly
  - Configure SSH profiles and use `target="ssh:profile"`

**❌ What Doesn't Work on Windows:**
- Local PowerShell/CMD sessions (`target="local"`)
- Local PTY (uses POSIX `pty` module)
- Local tmux (tmux not available on Windows)

**💡 Recommended Solution for Windows:**
Run the MCP server inside **WSL2** (Windows Subsystem for Linux):
- ✅ Full POSIX compatibility
- ✅ All features work (local + SSH)
- ✅ Access Windows files via `/mnt/c/`
- ✅ Native Linux environment

**WSL2 Setup:**
```bash
# Install WSL2 with Ubuntu
wsl --install

# Inside WSL2, install dependencies
sudo apt update
sudo apt install python3 tmux
pip install uv

# Run the server
uv run mcp-servers/terminal/main.py
```

## Requirements

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/)
- **POSIX host** (Linux/macOS) or **WSL2** (Windows)
- `tmux` installed on the target host when using `lifecycle="tmux"`

## Quick Start

**Linux/macOS:**
```bash
uv run mcp-servers/terminal/main.py
```

**Windows (WSL2):**
```bash
# Inside WSL2 terminal
uv run mcp-servers/terminal/main.py
```

**Windows (SSH-only, native):**
```powershell
# Native Windows PowerShell (SSH to Linux only)
uv run mcp-servers/terminal/main.py --sshConfig=mcp-servers/terminal/config.json
```

**With SSH profiles (all platforms):**
```bash
cp mcp-servers/terminal/config.template.json mcp-servers/terminal/config.json
# Edit config.json with your SSH server details
uv run mcp-servers/terminal/main.py --sshConfig=mcp-servers/terminal/config.json
```

## Tools

| Tool | Description |
|---|---|
| `open_session` | Start a session with `target`, `transport`, and `lifecycle` |
| `attach_tmux_session` | Attach MCP control to an existing tmux session (`sessionRef`) or pane (`paneRef`) |
| `send_session_input` | Send text or special keys |
| `capture_session_screen` | Get session screen (`text`, `ansi`, `structured`; supports `includeScrollback`, `joinWrappedLines`, `captureStart`, `captureEnd`) |
| `resize_tmux_session` | Resize dimensions for a tmux-backed session |
| `list_sessions` | List active sessions |
| `list_tmux_sessions` | List tmux sessions on local or SSH target |
| `detach_tmux_session` | Detach MCP control from a tmux session while leaving it running |
| `terminate_session` | Terminate a session (`SIGTERM`, `SIGKILL`, `SIGHUP`) |
| `exec_command` | Run one-shot shell commands on `local` or `ssh:<profile>` |
| `sudo_exec_command` | Run one-shot sudo commands on `local` or `ssh:<profile>` |
| `scp_upload` | Start async upload to `ssh:<profile>` via SFTP (returns `operationId`) |
| `scp_download` | Start async download from `ssh:<profile>` via SFTP (returns `operationId`) |
| `forward_remote_to_local` | Start async SSH local forwarding (`ssh -L`) (returns `operationId`) |
| `forward_local_to_remote` | Start async SSH remote forwarding (`ssh -R`) (returns `operationId`) |
| `tunnel_stop` | Stop an active tunnel by ID |
| `tunnel_list` | List active tunnels created by this server |
| `get_operation_status` | Check status/progress/result for async SCP/forward operations |

## `open_session` Model

- `target`
  - `local`
  - `ssh:<profile>`
- `transport`
  - `auto`: choose `pty` for common interactive CLIs, `pipe` otherwise; retry with `pty` on common TTY errors
  - `pty`: force PTY session
  - `pipe`: force normal stdin/stdout/stderr pipes
- `lifecycle`
  - `direct`: run process directly
  - `tmux`: run inside tmux (recommended for long-running workloads)

## Notes

- `tmux` lifecycle uses `tmux new-session`, `tmux send-keys`, and `tmux capture-pane`.
- `attach_tmux_session` defaults to pane `session:0.0` when using `sessionRef`; use `paneRef` to bind a specific pane.
- `detach_tmux_session` removes MCP binding but keeps tmux session running.
- `send_session_input` supports plain keys and modifier keys including `shift+arrow`, `alt+arrow`, and `ctrl+arrow`.
- For SSH targets, profiles are loaded from `--sshConfig`.
- `scp_*` and forwarding tools are non-blocking and require `target="ssh:<profile>"`; poll `get_operation_status(operationId)` for status.

## SSH Usage Guide

### SSH Connection Methods

This server supports two methods for accessing remote servers via SSH:

#### Method 1: Direct SSH (Current Implementation)
Uses Python's Paramiko library to establish direct SSH connections.

**Characteristics:**
- Built-in connection pooling for efficiency
- Works without local SSH client
- Configured via JSON profiles
- Supports PTY and pipe transports
- Direct channel control for terminal operations

**When to use:**
- Simple SSH configurations
- Environments without SSH client
- Need programmatic credential management
- Cross-platform consistency

#### Method 2: Local SSH CLI + Tmux (Performance Optimized)
Uses local `ssh` command wrapped in local `tmux` for maximum efficiency.

**Characteristics:**
- Single persistent SSH connection per session
- ~10x faster for repeated operations (local tmux commands only)
- Uses native SSH client features (ControlMaster, ProxyJump, agent forwarding)
- Leverages ~/.ssh/config
- Network resilient

**When to use:**
- High-frequency terminal interactions
- Complex SSH configurations (bastion hosts, ProxyJump)
- Need SSH agent forwarding
- Long-running remote sessions with tmux

**⚠️ Important:** With this method, MCP tools control the **local** tmux session. To use remote tmux or PTY, you must invoke it directly in the SSH command string (see examples below).

**Architecture comparison:**
```
Method 1 (Direct):
  MCP Tools
    ↓
  target="ssh:prod", lifecycle="tmux"
    ↓
  paramiko.exec_command("tmux send-keys...")  ← SSH round-trip per operation
    ↓
  Remote tmux session
    ↓
  Remote shell/process

Method 2 (Local Tmux + SSH):
  MCP Tools
    ↓
  target="local", lifecycle="tmux"
    ↓
  Local tmux send-keys (fast! no network)  ← 10x faster
    ↓
  Persistent SSH connection
    ↓
  Remote shell or remote tmux (optional)
    ↓
  Remote process

Key difference:
- Method 1: MCP → SSH exec → Remote tmux → Remote shell
- Method 2: MCP → Local tmux → SSH (persistent) → Remote shell

MCP lifecycle="tmux" parameter:
- Method 1: Controls REMOTE tmux
- Method 2: Controls LOCAL tmux (remote tmux must be in SSH command)
```

### SSH Profile Configuration

> **✅ Windows Users:** SSH features work perfectly on Windows 10/11 via Paramiko. You can manage remote Linux servers from Windows without WSL2.

Create `config.json` from template:

```bash
cp mcp-servers/terminal/config.template.json mcp-servers/terminal/config.json
```

Edit `config.json`:

```json
{
  "profiles": {
    "prod": {
      "host": "prod.example.com",
      "port": 22,
      "user": "deploy",
      "password": "",
      "key": "~/.ssh/id_rsa",
      "knownHosts": "~/.ssh/known_hosts",
      "timeoutMs": 60000,
      "maxChars": 1000,
      "sudoPassword": ""
    },
    "dev": {
      "host": "dev.example.com",
      "port": 2222,
      "user": "developer",
      "key": "~/.ssh/dev_key"
    }
  }
}
```

**Configuration fields:**
- `host` (required): Remote hostname or IP
- `port`: SSH port (default: 22)
- `user` (required): SSH username
- `password`: SSH password (optional, use key auth when possible)
- `key`: Path to private key file (recommended)
- `knownHosts`: Path to known_hosts file (default: auto-accept)
- `timeoutMs`: Connection timeout in milliseconds (default: 60000)
- `maxChars`: Max command length limit (default: 1000, set to `0` or `"none"` for unlimited)
- `sudoPassword`: Password for sudo operations (optional)

### Using SSH with Sessions

#### Method 1: Direct SSH (via MCP tools)

**Start remote session:**
```python
# Direct SSH with PTY
open_session(
    target="ssh:prod",
    command="bash",
    transport="pty",
    lifecycle="direct"
)

# With remote tmux (MCP manages remote tmux via SSH exec_command)
open_session(
    target="ssh:prod",
    command="python train.py",
    transport="pty",
    lifecycle="tmux"  # MCP creates/controls remote tmux
)
```

All MCP tools work directly:
```python
send_session_input(sessionId=sid, input="ls\n")
capture_session_screen(sessionId=sid)
```

#### Method 2: Local Tmux + SSH (Performance Optimized)

**⚠️ Important:** MCP tools control the **local** tmux. Remote commands must be in the SSH command string.

**Basic remote shell:**
```python
# Local tmux → SSH → Remote bash
open_session(
    target="local",
    command="ssh prod -t 'cd /app && bash'",
    transport="pty",
    lifecycle="tmux"  # Local tmux (MCP controlled)
)
```

**With remote tmux (nested):**
```python
# Local tmux → SSH → Remote tmux → Remote bash
open_session(
    target="local",
    command="ssh prod -t 'tmux new-session -A -s work -c /app'",
    transport="pty",
    lifecycle="tmux"  # Local tmux (MCP controlled)
)
```

**For long-running remote processes:**
```python
# Remote tmux keeps process alive even if SSH disconnects
open_session(
    target="local",
    command="ssh prod -t 'tmux new-session -A -s training \"python train.py\"'",
    transport="pty",
    lifecycle="tmux"
)
```

**Interacting with the session:**
```python
# All operations go through local tmux (fast!)
# Input is forwarded through SSH to remote shell
send_session_input(sessionId=sid, input="ls -la\n")
time.sleep(0.5)
output = capture_session_screen(sessionId=sid)

# To send commands to nested remote tmux, escape properly:
send_session_input(
    sessionId=sid,
    input="tmux send-keys -t work 'echo hello' Enter\n"
)
```

**Method comparison table:**

| Aspect | Method 1 (Direct) | Method 2 (Local Tmux + SSH) |
|--------|-------------------|----------------------------|
| MCP tmux control | Remote tmux | Local tmux |
| Remote tmux usage | `lifecycle="tmux"` | Manual in SSH command |
| Operations latency | Medium (SSH exec) | Fast (local tmux) |
| Setup complexity | Simple | Medium (nested if using remote tmux) |
| Use MCP tools | ✅ Direct | ✅ Via local tmux |
| Remote commands | MCP managed | String in SSH command |

**Practical example - Same workflow, both methods:**

```python
# Goal: Run remote Python REPL, execute code, get output

# ===== Method 1: Direct SSH =====
session = open_session(
    target="ssh:prod",
    command="python3",
    lifecycle="tmux"  # MCP creates remote tmux
)
# Behind the scenes: SSH exec "tmux new-session python3"

send_session_input(session.id, "2 + 2\n")
# Behind the scenes: SSH exec "tmux send-keys '2 + 2'"
# Latency: ~50ms (network round-trip)

output = capture_session_screen(session.id)
# Behind the scenes: SSH exec "tmux capture-pane"
# Latency: ~50ms (network round-trip)
# Total: ~100ms for send + capture

# ===== Method 2: Local Tmux + SSH =====
session = open_session(
    target="local",
    command="ssh prod -t python3",  # ← Python invoked via SSH
    lifecycle="tmux"  # MCP creates LOCAL tmux
)
# Behind the scenes: tmux new-session "ssh prod -t python3"

send_session_input(session.id, "2 + 2\n")
# Behind the scenes: tmux send-keys '2 + 2'
# ↑ Local command! Input forwarded through SSH
# Latency: ~5ms (local)

output = capture_session_screen(session.id)
# Behind the scenes: tmux capture-pane
# ↑ Local command! Captures local tmux buffer
# Latency: ~5ms (local)
# Total: ~10ms for send + capture ⚡

# Result: Same functionality, 10x faster!
```

**When to use nested remote tmux:**
```python
# Method 2 with remote tmux for maximum resilience
session = open_session(
    target="local",
    command="ssh prod -t 'tmux new-session -A -s training python3'",
    lifecycle="tmux"
)

# Layers:
# 1. Local tmux (MCP controlled, fast operations)
# 2. SSH connection (persistent)
# 3. Remote tmux (survives SSH disconnect)
# 4. Python process (survives remote tmux detach)

# Benefits:
# - Fast MCP operations (local tmux)
# - Process survives network issues (remote tmux)
# - Can reconnect: ssh prod -t 'tmux attach -t training'
```

### SSH Operation Examples

**Execute one-shot command:**
```python
exec_command(
    target="ssh:prod",
    command="df -h",
    timeoutMs=30000
)
```

**Execute sudo command:**
```python
sudo_exec_command(
    target="ssh:prod",
    command="systemctl restart nginx"
)
```

**File transfer:**
```python
# Upload
op_id = scp_upload(
    target="ssh:prod",
    localPath="/local/file.tar.gz",
    remotePath="/remote/file.tar.gz"
)

# Download
op_id = scp_download(
    target="ssh:prod",
    remotePath="/remote/logs.txt",
    localPath="/local/logs.txt"
)

# Check progress
get_operation_status(operationId=op_id)
```

**Port forwarding:**
```python
# Local forward (access remote service locally)
tunnel_id, local_port = forward_remote_to_local(
    target="ssh:prod",
    remoteHost="localhost",
    remotePort=5432,  # PostgreSQL on remote
    localPort=0       # Auto-assign local port
)

# Remote forward (expose local service remotely)
tunnel_id, remote_port = forward_local_to_remote(
    target="ssh:prod",
    localHost="localhost",
    localPort=8080,   # Local web server
    remotePort=9000   # Port on remote
)

# Stop tunnel
tunnel_stop(tunnelId=tunnel_id)
```

### Remote Tmux Sessions

**List remote tmux sessions:**
```python
list_tmux_sessions(target="ssh:prod")
```

**Attach to existing remote tmux:**
```python
attach_tmux_session(
    target="ssh:prod",
    sessionRef="my-session"  # or paneRef="my-session:0.1"
)
```

**Interactive workflow:**
```python
# 1. Create session
session = open_session(
    target="ssh:prod",
    command="bash",
    lifecycle="tmux",
    cols=80,
    rows=24
)

# 2. Send commands
send_session_input(
    sessionId=session.id,
    input="cd /app\n"
)

send_session_input(
    sessionId=session.id,
    input="./run_tests.sh\n"
)

# 3. Capture output
screen = capture_session_screen(
    sessionId=session.id,
    includeScrollback=True,
    joinWrappedLines=True,
    format="text"
)

# Variant: 200 history lines plus visible pane, with wrapped lines joined
screen = capture_session_screen(
    sessionId=session.id,
    captureStart="-200",
    joinWrappedLines=True,
    format="text"
)

# Variant: explicit full history through visible pane end
screen = capture_session_screen(
    sessionId=session.id,
    captureStart="-",
    captureEnd="-",
    joinWrappedLines=True,
    format="text"
)

# 4. Detach (keeps tmux running)
detach_tmux_session(sessionId=session.id)

# 5. Re-attach later
session = attach_tmux_session(
    target="ssh:prod",
    sessionRef="mcp-abc123"  # Original session name
)
```

### Performance Optimization

For high-frequency terminal interactions (e.g., AI agents, automation):

**Problem with Method 1:**
```python
# Method 1: Each MCP operation = new SSH exec_command
open_session(target="ssh:prod", lifecycle="tmux")
send_session_input(...)  # SSH exec: tmux send-keys
capture_screen(...)      # SSH exec: tmux capture-pane
# 2 operations = 2 SSH round-trips (~100-200ms)
```

**Solution with Method 2:**
```python
# Method 2: MCP operations are local only
open_session(
    target="local",
    command="ssh prod -t 'bash'",  # Or with remote tmux
    lifecycle="tmux"  # Local tmux controlled by MCP
)
send_session_input(...)  # Local: tmux send-keys (local tmux)
capture_screen(...)      # Local: tmux capture-pane (local tmux)
# 2 operations = 2 local commands (~10-20ms) ⚡
```

**Key insight:** With Method 2, the SSH connection stays open inside local tmux. All MCP tools interact with the local tmux session, which forwards input through the persistent SSH connection.

**For remote tmux + performance:**
```python
# Best of both worlds: Local tmux (fast MCP ops) + Remote tmux (resilience)
open_session(
    target="local",
    command="ssh prod -t 'tmux new-session -A -s work -c /app'",
    lifecycle="tmux"
)

# Now you have:
# - Fast MCP operations (local tmux commands)
# - Persistent SSH connection
# - Remote tmux for process survival
# - Can detach local tmux, SSH persists, remote tmux persists
```

**Enable SSH ControlMaster in ~/.ssh/config:**
```
Host prod
    HostName prod.example.com
    User deploy
    ControlMaster auto
    ControlPath ~/.ssh/sockets/%r@%h:%p
    ControlPersist 10m
```

Benefits:
- **10x faster** MCP operation latency (local vs SSH round-trip)
- Single SSH connection shared across operations
- Network resilient with connection persistence
- Full SSH client features available
- Can use nested remote tmux for additional resilience

### Security Best Practices

1. **Use key-based authentication:**
   ```json
   {
     "key": "~/.ssh/id_ed25519",
     "password": ""  // Leave empty
   }
   ```

2. **Protect config.json:**
   ```bash
   chmod 600 mcp-servers/terminal/config.json
   ```

3. **Use known_hosts verification:**
   ```json
   {
     "knownHosts": "~/.ssh/known_hosts"
   }
   ```

4. **Limit command length when needed:**
   ```json
   {
     "maxChars": 1000  // Prevent injection attacks
   }
   ```

5. **Avoid storing passwords:**
   - Use SSH agent for key management
   - Use sudo NOPASSWD in sudoers for automated sudo
   - Or use local SSH method with SSH agent forwarding

### Troubleshooting

**Connection fails:**
- Verify SSH credentials: `ssh -v user@host`
- Check firewall/security groups allow port 22
- Ensure host key is in known_hosts or disable `knownHosts`

**Slow operations:**
- Use local tmux + SSH method for high-frequency operations
- Enable SSH ControlMaster for connection reuse
- Check network latency: `ping host`

**Sudo command fails:**
- Set `sudoPassword` in profile, or
- Configure passwordless sudo on remote host, or
- Use local SSH method with `ssh -t` for interactive sudo

**Tmux not found:**
- Install on remote: `sudo apt install tmux` or `sudo yum install tmux`
- Verify PATH includes tmux location

**Windows: "POSIX host required" error:**
- For SSH operations: This error occurs but SSH features still work via Paramiko
- For local PowerShell: Not supported, use WSL2 instead
- Recommended: Run the entire MCP server inside WSL2 for full compatibility

### Windows Detailed Compatibility

**Architecture on Windows:**

The server has a POSIX check that blocks Windows, but SSH operations work because:
```
Windows Host
  ↓
Terminal MCP Server (Python + Paramiko - cross-platform)
  ↓
SSH Connection (Paramiko handles all POSIX operations remotely)
  ↓
Linux Remote Server (PTY, tmux, all features work here)
```

**Technical Limitations:**

Windows lacks POSIX modules required for local sessions:
- `pty` module (pseudo-terminal) - not available on Windows
- `fcntl` module (file control) - POSIX-only
- `termios` module (terminal I/O) - POSIX-only
- `os.killpg()` (process group signals) - not available on Windows
- tmux (terminal multiplexer) - not ported to Windows

**Workaround Options:**

1. **WSL2 (Recommended):**
   - Full POSIX environment on Windows
   - All features work natively
   - Can access Windows filesystem
   - Best for development and automation

2. **SSH-Only Mode (Windows Native):**
   - Remote server management works perfectly
   - No local session support
   - Good for managing Linux infrastructure from Windows
   - Uses Paramiko for all remote operations

3. **Remote Development:**
   - Run MCP server on Linux VM/container
   - Connect from Windows client
   - Supports both local (on Linux) and remote sessions

**Example Windows SSH Workflow:**

```python
# From Windows 10/11, manage a remote Linux server
# (SSH profile configured in config.json)

# ✅ Execute remote commands
exec_command(target="ssh:prod", command="docker ps")

# ✅ Start interactive remote session
session = open_session(
    target="ssh:prod",
    command="bash",
    lifecycle="tmux"  # tmux runs on remote Linux
)

# ✅ Send commands to remote
send_session_input(session.id, "cd /app && ls\n")

# ✅ Capture remote output
output = capture_session_screen(session.id)

# ✅ File transfer
scp_upload(
    target="ssh:prod",
    localPath="C:\\Users\\user\\deploy.zip",  # Windows path
    remotePath="/opt/app/deploy.zip"           # Linux path
)

# ✅ Port forwarding
tunnel_id, port = forward_remote_to_local(
    target="ssh:prod",
    remoteHost="localhost",
    remotePort=5432  # Access remote PostgreSQL from Windows
)
```

## MCP Config Example

```json
{
  "mcpServers": {
    "terminal": {
      "command": "uv",
      "args": [
        "run",
        "mcp-servers/terminal/main.py",
        "--sshConfig=mcp-servers/terminal/config.json"
      ]
    }
  }
}
```
