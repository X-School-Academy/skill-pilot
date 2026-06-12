# LinkedIn Publishing Workflow

## Discovery

Captured via agent-browser CDP on 2026-06-09.

## Flow

1. Navigate to `https://www.linkedin.com/feed/`
2. Click **"Start a post"** button (exact match — NOT substring match with "Post")
3. Fill textbox **"Text editor for creating content"**
4. Click **"Post"** button (exact match)
5. Verify: **"Post successful"** toast text appears, composer modal closes

## Key Selectors

| Element | Selector | Notes |
|---------|----------|-------|
| Post trigger | `button:has-text("Start a post")` exact | Always visible on feed page, opens modal |
| Composer textbox | `textbox[name="Text editor for creating content"]` | Inside modal |
| Post button | `button:has-text("Post"):not(:has-text("Start"))` | Must exclude "Start a post" substring match |
| Success toast | `text="Post successful"` | Appears after publish |

## Previous Issues

- **Substring match bug**: "Post" matched "Start a post" button behind the modal. Fixed by using exact match and `:not(:has-text("Start"))` exclusion.
- **False verification**: Checking for "Start a post" always passed because it's in the DOM behind the modal. Fixed by checking for "Post successful" toast instead.
- **Stale refs**: Button refs changed between snapshot and click. Fixed with retry loop.

## State

- **Status**: SCRIPT_VERIFIED
- **Last browser test**: 2026-06-09 — published successfully with retry
- **Last script test**: pending first run
