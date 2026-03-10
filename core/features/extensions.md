# Extensions

## Brief

Catalog of installable local extensions exposed from the WebUI, currently focused on Chrome and VS Code integration.

## User Value

- Surfaces extension packaging and install flows from inside Skill Pilot.
- Connects product features into browser and editor environments.
- Gives users a guided starting prompt instead of manual setup from scratch.

## Main Behavior

- Shows extension cards for supported local extensions.
- Builds an install prompt that points the agent to the extension folder.
- Sends the user into a new session to build and install the chosen extension.
- Currently references Chrome and VS Code extension targets.

## Related Features

- `mcp-servers.md`
- `skills-management.md`
- `security-cameras.md`

## Code References

- `core/webui/pages/index.tsx`
- `extensions/chrome/README.md`
- `extensions/chrome/package.json`
- `extensions/vscode/README.md`
- `extensions/vscode/package.json`
- Keywords: `EXTENSIONS`, `extensionInstall`, `extensions/chrome`, `extensions/vscode`

