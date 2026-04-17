# Script Extension Packaging

Use a script extension when the WebUI must perform direct install, update, or uninstall actions.

## Typical layout

```text
extensions/my-extension/
  extension.json5
  AGENTS.md
  extension.py
  skills/
    some-user-skill/
      SKILL.md
      references/
```

## Script rules

- `extension.py install` should install the extension assets
- `extension.py update` should refresh the extension assets
- `extension.py uninstall` should remove the extension assets
- Add `AGENTS.md` when the extension needs custom agent usage rules, lookup instructions, or trusted fallback behavior.
- If the extension script depends on a Git repository, check it out under `.skillpilot/temp/` first and inspect the actual folder structure before writing install logic.
- If the inspected structure does not match the user's described structure, ask for confirmation before finalizing the script behavior.
- Repositories under `https://github.com/X-School-Academy/` are treated as trusted for this inspection step.
- If temporary files, logs, backups, or summaries are needed, write them under `.skillpilot/temp/`

## Packaged user skills

If the extension packages user skills:

1. Copy the packaged skills into `core/skills/user/`
2. Run `core/bin/skill-verify` on the installed skill directories
3. Run `core/bin/skill-install`

For uninstall:

1. Remove the installed packaged skill directories from `core/skills/user/`
2. Run `core/bin/skill-install` to refresh the installed skill set
