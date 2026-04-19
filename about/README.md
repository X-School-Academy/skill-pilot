# About

This folder describes the current release of the Skill Pilot agent and tracks changes between releases.

## Files

- `version.json5` — the currently-applied Skill Pilot agent version and build.
- `CHANGELOG.md` — index of all released versions, newest first. Each entry links to a file under `changelog/`.
- `changelog/<version>.md` — the release notes for that version. One file per version. A single version may have multiple builds, each captured as a section inside the file (newest build on top).
- `AGENTS.md` — rules AI agents follow when they upgrade or restore this repo.

## Two separate version streams

Skill Pilot has two versions that move independently:

| Stream | File | What it versions |
|---|---|---|
| Skill Pilot agent | `about/version.json5` | Code, skills, workflows in this repo |
| Workspace | `workspace/config/version.json5` | Workspace folder structure and config format |

A new Skill Pilot release does not always require a workspace migration. When it does, the changelog entry for that release states the migration steps and the target workspace version.

## Version format

`<major>_<minor>_<patch>`, for example `1_00_00`. Underscores (not dots) keep the tag filesystem-friendly across all platforms.

Within a version, builds are integers (`1`, `2`, …). A new build within the same version is used for small fixes, doc-only changes, or staged rollouts that do not justify bumping the version number.

## Reading the changelog

Each `changelog/<version>.md` file looks like:

```
# <version>

## Build <n> — <YYYY-MM-DD> — <short title>

### Changes since previous
- …

### Upgrade notices
- …                                   (or `(none)`)

### Workspace target
workspace/config/version.json5 → <workspace-version>
```

If `Upgrade notices` contains steps, they must be applied in order when moving to that build.

If `Workspace target` differs from the previous build's target, the workspace must be migrated as described in the notices, and `workspace/config/version.json5` must be updated to the new target.

## Upgrading

Users do not edit this folder by hand. The `codeware-management` skill handles updates and restores, including walking pending changelog entries and bumping both version files. See `core/skills/system/codeware-management/`.
