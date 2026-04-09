# Demo And Capture Guidance

Use this reference when the user wants a live demo, a screenshot sequence, or source material for educational videos.

## Why Direct Terminal Routes Matter

The direct `/terminal?...` pages remove the left navigation shell and keep the browser frame focused on the terminal content.

This is useful when:

- teaching shell workflows
- showing an AI agent working in a terminal
- recording clean clips for demos
- capturing screenshots for slides, tutorials, or course assets

## Recommended Demo Flow

1. Open the WebUI through `get_webui_url`
2. If the demo is terminal-focused, switch to a direct `/terminal?...` URL
3. Keep the underlying work in a tmux-backed session so it remains stable while capturing
4. Use the browser automation skill to:
   - open pages
   - wait for stable content
   - capture screenshots
   - verify visible text and state between steps

## Capture Options

- Browser screenshots:
  - use `agent-browser screenshot`
- Page-state verification:
  - use `agent-browser snapshot -i`
- Terminal-history review:
  - use `/terminal/history?session=...`
- Desktop-level video capture when needed:
  - route to the `screen-recording` skill if the user wants an actual screen recording outside browser screenshots

## Practical Rule

- For feature walkthroughs, use the normal WebUI route first
- For shell or agent demonstrations, prefer the direct terminal route
- For repeatable educational assets, capture the same route and session shape each time
