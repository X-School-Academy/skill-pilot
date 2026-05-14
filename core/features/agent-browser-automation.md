# Feature Retrieval Index: Agent Browser Automation

## Retrieval Keywords

agent browser, browser automation, Playwright, playwright-cli, headless browser, headed browser, web automation, browser CLI, navigate, click, fill form, screenshot, extract data, web scraping, agent-browser, browser-automation, find-ui-element, local-openai-vision, chrome-devtool-proxy, Scrapling

## Scope

- Browser automation CLI for AI agents using Playwright
- Headed and headless browser modes
- Web interaction: navigate, click, fill, screenshot, extract
- Chrome DevTools proxy for advanced browser control
- Excludes: macOS screen/computer use (see `mac-screen-drawing-recording.md`)

## Main Behavior

- `core/bin/agent-browser` CLI launches and controls a browser session
- Playwright-backed; supports headed mode for visual interaction
- `find-ui-element` skill locates UI elements for automation
- `local-openai-vision` provides vision-based element detection
- Chrome DevTools proxy for additional browser control
- Scrapling extension for advanced web scraping

## Code Map

- `core/bin/agent-browser` — browser automation CLI
- `core/skills/system/find-ui-element/` — UI element finder skill
- `core/skills/system/local-openai-vision/` — vision-based element detection skill
- `core/engine/mcp_servers/media/playwright_utils/` — Playwright utilities shared with media MCP
- `.playwright-cli/` — Playwright browser profile directory
- `extensions/chrome-devtool-proxy/` — Chrome DevTools proxy
- `extensions/Scrapling/` — advanced web scraping extension
- `extensions/chrome/` — Chrome extension

## Search Commands

```bash
find core/skills/system/find-ui-element/ -type f
find core/skills/system/local-openai-vision/ -type f
ls .playwright-cli/Default/ | head -10
find extensions/chrome-devtool-proxy/ -type f
```

## Related Features

- `core/features/mac-screen-drawing-recording.md`
- `core/features/skill-agent-system.md`

## Update Notes

- Headed mode preferred for sites requiring user interaction/login state (per CLAUDE.md)
- `.playwright-cli/` stores browser profile; do not delete if login sessions need to persist
- Prompt injection warning: always warn user before loading untrusted websites via browser automation
