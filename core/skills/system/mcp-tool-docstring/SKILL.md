---
name: mcp-tool-docstring
description: Write MCP tool docstrings in the standard format so they map correctly to agent skill descriptions and body content when synced via mcp-to-skills. Use when adding or updating a system MCP tool docstring.
---

# Platform Builder - MCP Tool Docstring

This skill guides writing Python docstrings for system MCP tools (`@mcp.tool()`) in the format that the `mcp-to-skills` sync pipeline recognizes. When synced, the first line becomes the skill `description` field and the remaining content is placed at the top of the skill body.

## When to Use This Skill

- Adding a new `@mcp.tool()` function to a system MCP server
- Updating an existing system MCP tool docstring to follow the standard
- Reviewing a system MCP tool docstring for correctness

## Your Roles in This Skill

- **Backend Developer**: Write and validate the docstring structure
- **Technical Writer**: Ensure clarity, completeness, and correct formatting of each section

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

### Step 1: Write the Docstring

Follow this structure exactly:

```python
@mcp.tool()
def tool_name(param1: str, param2: int = 10) -> str:
    """One-line tool description under 1024 characters with no line breaks.

    Use this tool when you need to <describe the primary use case>.
    Best for <specific scenarios or input patterns>.

    Args:
        param1: Description of param1. Constraints or format notes.
        param2: Description of param2. Must be between X and Y.

    Returns:
        Description of what is returned. Include key fields if returning a dict or list.
        - field_name: what it contains

    Do not use this tool:
        - to <alternative action that has a better tool>
        - when <condition where another tool is preferred>

    Notes:
        - Any important behavioral details, ordering, edge cases.
        - If no matches found, returns an empty list.
    """
```

### Step 2: Validate the First Line

The first line of the docstring (immediately after the opening `"""`) must:

- Be a single line with **no line breaks**
- Be **under 1024 characters**
- Clearly describe **what the tool does** (not when to use it)
- End with a period

This line becomes the `description:` field in the generated `SKILL.md` frontmatter.

### Step 3: Write the Remaining Sections

After a blank line following the first line, include these sections as applicable:

| Section | Required | Purpose |
|---|---|---|
| Use this tool when | Recommended | Describes when to invoke this tool |
| Args | Required if params exist | One entry per parameter with type hints |
| Returns | Required | Describes the return value and structure |
| Do not use this tool | Recommended | Lists cases where another tool is better |
| Notes | Optional | Edge cases, ordering, limits, caveats |

The remaining content (everything after the first line) is placed at the **top of the skill body** in the generated `SKILL.md`, before the `## Usage` section.

### Step 4: Verify Against the Sync Behavior

The `mcp-to-skills` sync pipeline (`core/engine/mcp_servers/mcp_to_skills/sync.py`) processes system tool docstrings as follows:

1. Normalizes the full docstring (dedent + strip)
2. Splits on the first line → **skill description** (frontmatter `description:`)
3. Takes the remaining lines → **prepended to skill body** before `## Usage`
4. The full schema is appended as `## Arguments Schema`

Non-system MCP tools are unaffected — they use `build_short_description` on the full description as before.

### Step 5: Run Skill Sync

After updating the tool docstring, restart or reload the engine and re-sync:

```bash
core/bin/tool-cli engine-reload
```

Or run the sync script directly:

```bash
core/bin/tool-cli mcp-sync <server-id>
```

Verify the generated `SKILL.md` in `core/skills/system/` has the correct description and body.

## Key Principles

- **First line only**: Never put `\n` in the first docstring line
- **1024 char limit**: Keep the first line under 1024 characters (the skill spec limit)
- **Sections are optional**: Include only sections that add real value; omit empty sections
- **System tools only**: This docstring format is only used by system MCP servers where source code is under our control; third-party MCP servers are unaffected

## Common Issues

**Issue: First line is blank (docstring starts with a newline)**
- Solution: Put the description text on the same line as `"""` or on the first non-blank line. After `normalize_description`, the first non-blank line is used.

**Issue: Description too long**
- Solution: Keep the first line under 1024 characters. Move extra context to the "Use this tool when" paragraph.

**Issue: Sync still shows old description**
- Solution: Restart the MCP server or reload the engine so the updated docstring is exposed via the MCP protocol, then re-run the sync.

**Issue: Skill body is empty (no extra content)**
- Solution: If the docstring is a single line, only the frontmatter description is set; no extra body content is added. This is valid for simple tools.
