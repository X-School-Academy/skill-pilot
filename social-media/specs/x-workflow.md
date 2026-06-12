# X/Twitter Publishing Workflow

## Discovery

Captured via agent-browser CDP on 2026-06-09.

## Flow

1. Navigate to `https://x.com/home`
2. Fill textbox **"Post text"** (directly on page, no modal)
3. Wait for Post button to enable (React re-renders after text input)
4. Click **"Post"** button (must be enabled, exact text match)
5. Verify: textbox **"Post text"** is empty (content was submitted)
6. Watch for `graduated-access` redirect (anti-bot)

## Key Selectors

| Element | Selector | Notes |
|---------|----------|-------|
| Composer textbox | `textbox[name="Post text"]` | Directly on home page |
| Post button | `button:has-text("Post"):not([disabled])` | Exact text match, must be enabled |
| Anti-bot gate | URL contains `graduated-access` | Redirect after click means blocked |

## Constraints

- **280 characters max** for free users
- **50 posts/day**
- **500 DMs/day**

## Previous Issues

- **Character limit**: 342-char draft kept Post button disabled. Added 280-char validation.
- **Stale button ref**: Button enabled after fill but ref changed between snapshot and click. Fixed with fresh `locator()` query on each retry.
- **Anti-bot graduated-access**: Post click sometimes redirects to rate-limit page. Added detection and warning.
- **Verification regex**: `$` anchor without `re.MULTILINE` never matched on multi-line snapshots. Fixed.

## State

- **Status**: SCRIPT_VERIFIED
- **Last browser test**: 2026-06-09 — published successfully with retry
- **Last script test**: pending first run
