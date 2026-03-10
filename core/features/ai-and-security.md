# AI And Security

## Brief

Settings surface for provider-level security controls and environment safe-guard status.

## User Value

- Lets users define how much autonomy the system should have in sensitive flows.
- Centralizes session security defaults and provider-specific overrides.
- Exposes env safe-guard state in the same UI.

## Main Behavior

- Loads saved security settings from config.
- Edits fixed feature security sections such as schedules, new session, remote bot, and dev swarm.
- Supports provider-specific `skillAgent` overrides.
- Saves the resulting settings back to engine config.
- Displays and updates env safe-guard status and related status messaging.

## Related Features

- `new-session.md`
- `schedules.md`
- `discord-bot.md`
- `profile.md`

## Code References

- `core/webui/pages/index.tsx`
- `core/engine/routes.py`
- `core/skills/system/key-safe/SKILL.md`
- Keywords: `securitySettings`, `SECURITY_SECTION_DEFS`, `setSectionSecurityFlag`, `setProviderSecurityFlag`, `envSafeguardEnabled`, `envSafeguardMessage`
- API routes: `/api/config/settings`

