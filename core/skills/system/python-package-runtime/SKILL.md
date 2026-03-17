---
name: python-package-runtime
description: Use when a task needs to install a new Python package, run a Python helper script, or a Python package CLI.
---

# AI Builder - Python Package Runtime

Use this skill to install Python packages and run Python-based helpers in a consistent repo-safe way.

## When to Use This Skill

- A task needs a new Python package installed in this repo
- A helper script should be run with the repo Python environment
- A Python package exposes a CLI that should be run from the engine virtualenv

## Your Roles in This Skill

- **Platform Engineer**: Keep Python package installation and runtime behavior consistent with the repo environment
- **Backend Developer**: Run scripts and package CLIs with the correct interpreter and virtualenv paths
- **Technical Writer**: Document the exact command conventions clearly and tersely

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Decide what kind of Python action is needed

Choose one path:

1. Install one or more new Python packages
2. Run a Python helper script
3. Run a package-provided CLI from the engine virtualenv

### Step 2: Install packages with the repo wrapper only

For any new Python package in this repo, always install it from repo root with:

```bash
core/bin/uv-install <package> [package...]
```

This wrapper runs `uv add` in `core/engine/`. Do not use `pip install` directly for new packages.

### Step 3: Run Python scripts with the repo interpreter

Run helper scripts with:

```bash
core/bin/python path/to/script.py
```

`core/bin/python` points to `core/engine/.venv/bin/python`, so scripts run with the repo-managed environment and installed packages.

### Step 4: Run package CLIs from the engine virtualenv

When a package provides a CLI entrypoint, run it from:

```bash
core/engine/.venv/bin/<cli-name>
```

If you need to confirm the binary name, inspect `core/engine/.venv/bin/` first.

### Step 5: Keep helpers and temp artifacts contained

- Put temporary helper scripts and intermediate files under `.skillpilot/temp/`
- Keep commands relative to repo root unless the task requires another working directory
- Prefer small, one-purpose helpers over ad hoc command variations

## Expected Output

- The required package is installed through `core/bin/uv-install`, if installation was needed
- Python scripts run through `core/bin/python`
- Package CLIs run from `core/engine/.venv/bin/`
- The result clearly states which path was used

## Key Principles

- Use one installation path: `core/bin/uv-install`
- Use one Python interpreter path: `core/bin/python`
- Use one CLI path convention: `core/engine/.venv/bin/<cli-name>`
- Do not bypass the repo environment with direct `pip install` or a random system Python
