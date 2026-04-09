---
name: skill-pilot-webui
description: >-
  Open and operate the local Skill Pilot WebUI through the browser for demos, walkthroughs, settings changes, task execution, and terminal-based education flows. Use when the user wants the agent to drive Skill Pilot as a human would in the browser, open a specific WebUI feature, or jump directly into shell or agent terminal views.
---

# Skill Pilot WebUI

Use this skill to drive the local Skill Pilot WebUI with browser automation instead of describing the UI abstractly.

## When to Use This Skill

- The user wants the agent to open or demo the Skill Pilot WebUI
- The user wants settings or feature changes made through the browser UI
- The user wants screenshots or recordings of Skill Pilot usage flows
- The user wants to open a direct shell or agent terminal page without the left navigation
- The user wants a feature-specific walkthrough routed by the left nav menu

## Your Roles in This Skill

- **QA Engineer**: Navigate the WebUI, verify the visible state, and capture screenshots or recordings for demos
- **Technical Writer**: Route the agent to the correct feature reference and keep the UI workflow understandable
- **DevOps Engineer**: Resolve the live local WebUI URL and open the correct direct terminal/session routes

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Open the live Skill Pilot WebUI

- Get the current local URL with `core/bin/tool-cli get_webui_url`
- If the user explicitly wants development mode, use `core/bin/tool-cli get_webui_url --dev`
- If the command fails because the engine is not started, start Skill Pilot first:
  - production or runtime-default mode: `./skillpilot.sh start`
  - development mode: `./skillpilot.sh start --dev`
- Open the returned URL with the `agent-browser` skill
- Treat this as a trusted local site unless the user has proxied it through some other host

- For exact commands and browser flow, refer to `references/open-and-auth.md`

### Step 2: Route by feature instead of guessing

- Inspect the left navigation or use the known nav map
- Choose the matching reference file for the requested feature
- Use the browser to navigate and verify the expected page or in-page view before taking action

- For the nav map and routing table, refer to `references/left-nav-map.md`
- For root-page embedded views and settings areas, refer to `references/home-views.md`
- For dedicated workspace pages, refer to `references/workspace-pages.md`

### Step 3: Use direct terminal pages when the left nav should be hidden

- For shell demos, browser-based terminal teaching, screenshots, or recordings, open the direct terminal page instead of the full app shell
- Use the direct `/terminal` routes so the content area shows only the terminal view

- For direct shell-terminal usage, refer to `references/terminal-shell.md`
- For direct agent-session usage, refer to `references/terminal-agent.md`

### Step 4: Capture demos and education assets

- When the user wants a walkthrough, demo, education screenshots, or clips, prefer driving the WebUI with browser automation and direct terminal pages
- Use tmux-backed sessions so the terminal content stays live while the browser view is captured
- After important UI transitions, capture screenshots and verify what is visible before continuing

- For demo and capture guidance, refer to `references/demo-capture.md`

## Expected Output

- The requested Skill Pilot WebUI feature is opened and operated in the browser
- If the task is terminal-focused, the direct terminal page is opened without the left nav shell
- If the user requested demo assets, the run includes screenshots or recordings of the browser flow

## Key Principles

- Always use the live URL from `core/bin/tool-cli get_webui_url` instead of assuming the port
- Prefer feature-specific references over improvising the UI structure
- Use direct terminal routes for shell and agent demos so the recording frame stays clean
- Verify the visible page state with the browser before making claims about the UI
