# NPM Publish Reference

This reference expands the npm publishing workflow with concrete checks, metadata expectations, and common fixes.

## Prerequisites

Required tools and access:

- Node.js (includes npm)
- Git
- GitHub repository
- npm account

Verification commands:

```bash
node -v
npm -v
git --version
```

## npm Account Access

- Create an account at `https://www.npmjs.com` if needed.
- Log in from the CLI:

```bash
npm login
```

- Confirm identity:

```bash
npm whoami
```

## Recommended Project Layout

```
project-root/
├─ package.json
├─ README.md
├─ LICENSE
├─ index.js        # or dist/
└─ .gitignore
```

## package.json Essentials

Required fields:

```json
{
  "name": "your-package-name",
  "version": "1.0.0",
  "description": "Short description of the package",
  "main": "index.js",
  "license": "MIT"
}
```

Naming rules:

- Must be unique on npm
- Lowercase only
- No spaces
- Use `-` instead of `_`

Check availability:

```bash
npm view your-package-name
```

## GitHub Metadata (Recommended)

Repository:

```json
{
  "repository": {
    "type": "git",
    "url": "https://github.com/ORG/REPO.git"
  }
}
```

Homepage:

```json
{
  "homepage": "https://github.com/ORG/REPO#readme"
}
```

Issues:

```json
{
  "bugs": {
    "url": "https://github.com/ORG/REPO/issues"
  }
}
```

## README Minimum

```md
# Package Name

## Installation
npm install package-name

## Usage
Example usage here

## License
MIT
```

## Versioning (SemVer)

Published versions cannot be overwritten. Use:

```bash
npm version patch
npm version minor
npm version major
```

This updates `package.json`, creates a git commit, and tags the release.

## Publish Workflow

Dry run:

```bash
npm pack
```

Publish public package:

```bash
npm publish --access public
```

Scoped package example:

```json
{
  "name": "@org/package-name"
}
```

Use the same `--access public` flag unless you want a private release.

## Package Contents Control

Prefer the `files` field:

```json
{
  "files": ["dist", "index.js"]
}
```

Or use `.npmignore`:

```
node_modules
src
tests
.env
```

## Pre-Publish Checklist

- `npm whoami` works
- Version bumped
- `repository`, `homepage`, and `bugs` configured
- README present
- No secrets or private files included
- `npm pack` reviewed

## Common Errors

403 Forbidden:

- Version already exists
- Not logged in
- Missing `--access public`

402 Payment Required:

- Scoped package defaulted to private

Fix with:

```bash
npm publish --access public
```

## Post-Publish Tasks

```bash
npm deprecate pkg "message"
npm owner add user pkg
npm owner ls pkg
```

Unpublish (within npm time limits):

```bash
npm unpublish pkg@version
```

## Best Practices

- Prefer scoped packages
- Release from `main`
- Tag releases consistently
- Maintain a changelog
- Automate with CI (e.g., GitHub Actions)
- Never publish secrets

## Reference Commands

```bash
npm login
npm whoami
npm version patch
npm publish --access public
npm pack
```
