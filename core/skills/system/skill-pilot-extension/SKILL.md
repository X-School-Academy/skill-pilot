---
name: skill-pilot-extension
description: Create, update, install, uninstall, or use Skill Pilot extensions under `extensions/`, including optional extension-specific agent guidance.
---

# AI Builder - Skill Pilot Extension

This skill creates or updates Skill Pilot extensions that appear in the WebUI Extensions screen.

## When to Use This Skill

- The user asks to create a new extension under `extensions/`
- The user asks to update an existing Skill Pilot extension
- The user wants to add or change `extension.json5`
- The user wants to add a `prompt`, `skill`, or `script` extension type
- The user asks to use an extension under `extensions/<name>`
- The user wants an extension installer script or packaged extension assets added or updated
- The user asks to install, update, or uninstall an existing extension

## Your Roles in This Skill

- **Project Manager**: Clarify the extension goal, choose the correct extension type, and keep the work aligned with the WebUI extension contract.
- **Backend Developer (Engineer)**: Create or update extension folders, metadata files, installer scripts, and any packaged extension assets.
- **Technical Writer**: Keep extension metadata and supporting docs concise, correct, and maintainable.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Resolve the extension target

- Determine whether the task is for a new extension or an update.
- Resolve the extension folder under `extensions/`.
- If no folder name is provided, choose a concise kebab-case name that matches the extension purpose.

### Step 2: Choose the correct extension type

- Use `prompt` when the WebUI should open a new agent session using a configured prompt.
- Use `skill` when the WebUI should open a new agent session that invokes an installed agent skill.
- Use `script` when the WebUI should run `install`, `update`, or `uninstall` through `extension.py`.
- Refer to `references/extension-contract.md` for the exact metadata contract and runtime behavior.

### Step 3: Create or update extension metadata

- Create or update `extension.json5` in the extension root.
- Always include `name`, `description`, and `type`.
- If `type` is `prompt`, include `prompt`.
- If `type` is `skill`, include `skill`.
- If `type` is `script`, include `script` only when not using the default `extension.py`.
- Include `entrypoint` when the extension has an HTML page the WebUI should serve (e.g. `index.html`).
- Include `installed` (defaults to `false`); script extensions must update this field after successful install/uninstall.

### Step 4: Add extension implementation files

- For `prompt`, keep the prompt generic because the WebUI appends the extension path separately.
- For `skill`, ensure the referenced agent skill exists and is the right category for the task.
- For `script`, add or update `extension.py` and support `install`, `update`, and `uninstall`.
- When the extension needs agent-specific operating instructions, add `extensions/<extension-name>/AGENTS.md`.
- `AGENTS.md` is optional, but create it when the extension needs custom usage rules, lookup rules, trust boundaries, or fallback guidance for future agents.
- If the script depends on a Git repository, check out the repository to `.skillpilot/temp/` and understand its structure before writing the script.
- If the checked-out structure differs materially from the user's instruction, stop and ask the user to confirm the intended behavior before creating or changing the script.
- Repositories under `https://github.com/X-School-Academy/` are trusted for this inspection step and do not require an extra trust confirmation.
- If the script needs temporary or intermediate files, write them under `.skillpilot/temp/`.
- Refer to `references/script-extension-packaging.md` for script layout and lifecycle guidance.

### Step 5: Run install, update, or uninstall when requested

When the user asks to install, update, or uninstall an existing extension:

- Locate the extension folder under `extensions/` and read its `extension.json5`.
- Before using the extension, check whether `extensions/<extension-name>/AGENTS.md` exists.
- If that `AGENTS.md` exists, read it and follow its instructions before inspecting extension code or assets.
- If that `AGENTS.md` does not exist, tell the user there is no extension-specific `AGENTS.md` and offer to inspect the extension code to determine how to use it.
- For `script` extensions, run the action via `core/bin/python {ext-path}/extension.py {action}` where `{action}` is `install`, `update`, or `uninstall`.
- For `prompt` extensions, start a new session using the configured `prompt` with the extension path appended.
- For `skill` extensions, start a new session that invokes the referenced agent skill.
- After a successful `install` or `update`, verify that `installed` is set to `true` in `extension.json5`.
- After a successful `uninstall`, verify that `installed` is set to `false` in `extension.json5`.

### Step 6: Validate and document

- Ensure the extension is discoverable by the WebUI by keeping `extension.json5` in the extension root.
- If the extension adds reusable user skills, validate them with `core/bin/skill-verify` and refresh installed skills with `core/bin/skill-install`.
- Update extension documentation when the metadata contract or install flow changes.

## Expected Output

- A ready-to-use extension folder under `extensions/`
- Valid `extension.json5` metadata
- Any required `extension.py`, packaged assets, and supporting docs

## Key Principles

- Keep the extension contract data-driven rather than hard-coded in the WebUI
- Keep prompt extension text generic and let the WebUI append the extension path
- Keep extension implementation scoped to that extension folder
- Use extension-local `AGENTS.md` files for custom agent behavior when an extension needs usage-specific instructions
- Prefer concise `SKILL.md` instructions and move detailed operational rules into reference files
