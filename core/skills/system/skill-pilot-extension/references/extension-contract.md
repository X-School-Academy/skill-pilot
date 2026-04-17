# Extension Contract

Skill Pilot WebUI discovers extensions from direct subfolders of `extensions/`.

Each extension folder must contain `extension.json5`.
An extension folder may also contain `AGENTS.md` with extension-specific operating instructions for agents.

Supported keys:

- `name`
- `description`
- `version`: optional, documentation only
- `license` or `licence`: optional, documentation only
- `type`: `prompt` | `skill` | `script`
- `prompt`: required for `prompt`
- `skill`: required for `skill`
- `script`: optional for `script`, defaults to `extension.py`
- `entrypoint`: optional; when set to an HTML file (e.g. `index.html`), the WebUI shows a **View** button that serves the extension folder as a static website rooted at the extension directory
- `installed`: optional, defaults to `false`; automatically set to `true` after a successful install and `false` after uninstall; controls which buttons appear (Install vs Update/Uninstall/View)

## Runtime behavior

- `prompt`: the WebUI opens a new session using the configured `prompt`, then appends `Extension path: extensions/{dir}`
- `skill`: the WebUI opens a new session using `Use agent skill {skill} to install extension ...`
- `script`: the WebUI shows `Install`, `Update`, and `Uninstall` buttons and runs the backend action endpoint

## Optional `AGENTS.md`

- Before using an extension, agents should check for `extensions/{dir}/AGENTS.md`.
- If it exists, agents should read and follow it before inspecting extension code or assets.
- If it does not exist, agents should say so and offer to inspect the extension code to determine usage details.

## `installed` field lifecycle

Script extensions must update `installed` in `extension.json5` on success:

- After a successful `install` or `update`: set `installed` to `true`
- After a successful `uninstall`: set `installed` to `false`

This ensures the WebUI shows the correct buttons (Install vs Update/Uninstall/View).
