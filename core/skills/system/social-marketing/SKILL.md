---
name: social-marketing
description: Create, schedule, and publish content for LinkedIn, Xiaohongshu (小红书), and X. Handles platform-specific copywriting, engagement frequency tracking via local history, and browser-based publishing.
---

# AI Builder - Social Marketing

Automate end-to-end social media workflows. This skill manages content strategy, high-conversion copywriting for specific platforms, and automated browser interactions while maintaining a publishing history to prevent spamming.

## When to Use This Skill

- User wants to draft or publish a post to LinkedIn, X, or Xiaohongshu.
- User needs to check when they last posted to avoid over-posting.
- User wants to repurpose a single topic into multiple platform-specific formats.

## Your Roles in This Skill

- **Social Media Manager**: Responsible for checking `.skillpilot/social-marketing-history.json` to manage posting frequency and recording new activity.
- **Expert Copywriter**: Crafts platform-specific copy (e.g., professional for LinkedIn, "vlog-style" for XHS).
- **DevOps Engineer**: Orchestrates the `agent-browser` tool to perform UI actions based on platform selectors.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight.

## Instructions

Follow these steps in order:

### Step 1: Initialize and Check History

Read `.skillpilot/social-marketing-history.json`.

- If it doesn't exist, create it with `{"posts": [], "next_scheduled": {}}`.
- Check the `timestamp` of the last post for the target platform.
- **Rule**: If the last post was less than 24 hours ago, warn the user and suggest a better time based on the frequency guidelines in `references/`.

### Step 2: Platform-Specific Copywriting

Generate the content based on the user's topic:

- If posting to **LinkedIn**, follow `references/linkedin.md`.
- If posting to **Xiaohongshu**, follow `references/xiaohongshu.md`.
- If posting to **X (Twitter)**, follow `references/x.md`.
- **Mandatory Approval**: You must display the generated text (and image descriptions if applicable) and wait for the user to say "Approve" or "Publish".

### Step 3: Execute Publishing Flow

**Primary path (script-based, no AI):** Use `core/bin/social-publish <draft-path> <platform>` to publish. The script handles browser automation, validation, and history recording without consuming AI tokens.

```
core/bin/social-publish linkedin/my-post.md linkedin
```

**Fallback path (manual, AI-driven):** If the script fails (e.g., LinkedIn changed its UI), fall back to manual browser automation:

Use `core/bin/agent-browser --headed` to navigate to the platform.

1. **Auth Check**: If not logged in, stop and ask the user to complete login in the headed browser.
2. **UI Navigation**: Use the specific selectors (input boxes, publish buttons) documented in the respective platform file in `references/`.
3. **Drafting**: Input the approved text and attach any required assets.

After a successful manual publish, update `core/bin/social-publish` with the new selectors so the script works again for future posts.

### Step 4: Record and Report

After publishing:

1. If using `core/bin/social-publish`, history is updated automatically.
2. If using the manual fallback, update `.skillpilot/social-marketing-history.json` with the post content, platform, and timestamp.
3. Output a summary including the platform used and the next recommended posting window.

## Key Principles

- **Context Preservation**: Output result as plain text. If the user asked to save it to a file, write it there.
- **Human-in-the-Loop**: Never click "Publish" without explicit user confirmation of the text.
- **Memory-First**: Always check history before generating content to ensure the strategy is consistent.
