# Extensions

The WebUI Extensions screen discovers extensions dynamically from subfolders under `extensions/`.

## How discovery works

- Each direct subfolder of `extensions/` is checked for `extension.json5`.
- If the file is missing, the folder is skipped.
- If the file exists and is valid, the extension appears in the WebUI.
- An extension folder may also include an optional `AGENTS.md` file with extension-specific instructions for agents.

## `extension.json5`

Supported keys:

- `name`
- `description`
- `version`: optional, documentation only
- `license` or `licence`: optional, documentation only
- `type`: `prompt` | `skill` | `script`
- `prompt`: required when `type` is `prompt`
- `skill`: required when `type` is `skill`
- `script`: optional when `type` is `script`; defaults to `extension.py`
- `entrypoint`: optional; when set to an HTML file (e.g. `index.html`), the WebUI shows a **View** button that serves the extension folder as a static website rooted at the extension directory
- `installed`: optional, defaults to `false`; automatically set to `true` after a successful install and `false` after uninstall; controls which buttons appear (Install vs Update/Uninstall/View)

Example prompt extension:

```json5
{
  name: 'Skill Pilot Chrome Extension',
  description: 'Browser extension for integrating Skill Pilot with Chrome.',
  version: '0.1.0',
  license: 'MIT',
  type: 'prompt',
  prompt: 'Build and install this extension.',
}
```

Example skill extension:

```json5
{
  name: 'My Installer Skill',
  description: 'Installs the extension through an agent skill.',
  type: 'skill',
  skill: 'my-installer-skill',
}
```

Example script extension:

```json5
{
  name: 'My Python Extension',
  description: 'Uses a Python installer script.',
  type: 'script',
  script: 'extension.py',
}
```

## Optional `AGENTS.md`

Extensions may include `AGENTS.md` in the extension root:

```text
extensions/my-extension/
  extension.json5
  AGENTS.md
  extension.py
```

Use `AGENTS.md` when an extension needs custom agent guidance such as:

- how to use the extension
- where to look for extension-specific reference files
- trusted fallback behavior
- rules for when to inspect code versus follow packaged documentation

When an agent is asked to use an extension:

- it should first check whether `extensions/{dir}/AGENTS.md` exists
- if it exists, the agent should read and follow that file before inspecting extension code or assets
- if it does not exist, the agent should say so and offer to inspect the extension code to determine usage details

## WebUI behavior by type

### `prompt`

The WebUI starts a new session using the configured `prompt`, then appends the extension path separately:

```text
{prompt}

Extension path: extensions/{dir}
```

### `skill`

The WebUI starts a new session with this prompt:

```text
Use agent skill {skill} to install extension "{name}" in extensions/{dir}.
```

### `script`

The WebUI shows `Install`, `Update`, and `Uninstall` buttons.

It runs:

```bash
core/bin/python {ext-path}/extension.py install
core/bin/python {ext-path}/extension.py update
core/bin/python {ext-path}/extension.py uninstall
```

If `script` is set in `extension.json5`, that filename is used instead of `extension.py`.

## Python script contract

For `script` extensions, create a Python entrypoint in the extension folder.

The script must accept one argument:

- `install`
- `update`
- `uninstall`

Example:

```python
import sys


def main() -> int:
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "install":
        print("installing")
        return 0
    if action == "update":
        print("updating")
        return 0
    if action == "uninstall":
        print("uninstalling")
        return 0
    print("expected install, update, or uninstall", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```
