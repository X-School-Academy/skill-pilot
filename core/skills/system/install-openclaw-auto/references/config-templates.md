# Config Templates (Agent-Friendly)

OpenClaw reads JSON5 from `~/.openclaw/openclaw.json`.

## Minimal secure baseline

```json5
{
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace",
      model: { primary: "anthropic/claude-sonnet-4-5" },
      models: {
        "anthropic/claude-sonnet-4-5": {},
      },
    },
  },

  gateway: {
    mode: "local",
    port: 18789,
    bind: "loopback", // use "lan" for 0.0.0.0
    auth: {
      mode: "token",
      token: "REPLACE_WITH_LONG_RANDOM_TOKEN",
    },
    controlUi: {
      enabled: true,
    },
  },
}
```

## Bind mode variants

### Localhost-only

```json5
{ gateway: { bind: "loopback" } }
```

### Listen on `0.0.0.0`

```json5
{ gateway: { bind: "lan", auth: { mode: "token", token: "REQUIRED" } } }
```

## Channel snippets

### WhatsApp

```json5
{
  channels: {
    whatsapp: {
      enabled: true,
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      groups: { "*": { requireMention: true } },
    },
  },
}
```

### Telegram

```json5
{
  channels: {
    telegram: {
      enabled: true,
      botToken: "123456:abc",
      dmPolicy: "pairing",
      groupPolicy: "allowlist",
      groups: { "*": { requireMention: true } },
    },
  },
}
```

### Discord

```json5
{
  channels: {
    discord: {
      enabled: true,
      token: "DISCORD_BOT_TOKEN",
      groupPolicy: "allowlist",
      dm: { policy: "pairing" },
    },
  },
}
```

### Slack (Socket Mode)

```json5
{
  channels: {
    slack: {
      enabled: true,
      mode: "socket",
      appToken: "xapp-...",
      botToken: "xoxb-...",
      groupPolicy: "allowlist",
      dm: { policy: "pairing" },
    },
  },
}
```

## Token generation

Use helper script:

```bash
node core/skills/system/install-openclaw-auto/scripts/generate-token.js
```

## Validate + inspect

```bash
openclaw doctor
openclaw config get gateway.bind
openclaw config get gateway.auth.mode
```
