# WSL Distribution Selection Guide

Use this guide when the user asks which Linux distribution to install with WSL.

## Recommended Defaults

- **Default for most users:** `Ubuntu-22.04`
- **Latest Ubuntu option:** `Ubuntu-24.04`
- **Stable non-Ubuntu option:** `Debian`
- **Security testing use case:** `kali-linux`

If the user is not sure, choose `Ubuntu-22.04`.

## Friendly Name to WSL Name Mapping

Use these mappings before running install scripts:

- `ubuntu` -> `Ubuntu-22.04`
- `ubuntu-22.04` -> `Ubuntu-22.04`
- `ubuntu-24.04` -> `Ubuntu-24.04`
- `ubuntu-20.04` -> `Ubuntu-20.04`
- `debian` -> `Debian`
- `kali` -> `kali-linux`
- `kali-linux` -> `kali-linux`
- `opensuse` -> `openSUSE-Tumbleweed`
- `opensuse-tumbleweed` -> `openSUSE-Tumbleweed`

## How to Validate Available Distributions

In elevated PowerShell:

```powershell
wsl --list --online
```

If a requested name is not available, ask the user to pick one from the output and rerun installation.

## Selection Rules

1. Preserve explicit user choice when valid.
2. If user gives a common alias, normalize to the mapped canonical name.
3. If unavailable, fail fast and provide suggested alternatives.
4. Do not silently switch to a different distro unless the user approves.
