# Find Subagent

Use this reference when the user asks to find, inspect, summarize, or dynamically use a Skill Pilot subagent.

## Subagent Folders

Search these folders:

- `core/subagents/user/`
- `core/subagents/system/`

Do not search ignored paths. Respect any ignore file that applies to the repository.

## Steps

### Step 1: Search Source Definitions

Use `rg` first where possible:

```bash
rg --files core/subagents/user core/subagents/system -g '*.md'
```

```bash
rg -n "<subagent-name-or-keyword>" core/subagents/user core/subagents/system -g '*.md'
```

If `rg` is unavailable, use `find` and `grep`.

### Step 2: Inspect Candidate Metadata

Read only enough frontmatter and prompt body to determine whether the subagent matches:

- `name`
- `description`
- first few prompt-body paragraphs if needed

### Step 3: Choose the Correct Subagent

Prefer:

1. exact `name` match
2. exact filename match
3. strongest description match for the requested task
4. user-level subagent over system-level when the user intent is personal/project-specific

If no candidate clearly matches, report that the subagent was not found and list the closest candidates.

### Step 4: Inspect Installed Outputs When Needed

If the user asks about installed output or code-agent compatibility, inspect target folders:

- `.claude/agents/`
- `.codex/agents/`
- `.gemini/agents/`
- `.opencode/agents/`

For OpenCode, verify the generated file includes:

```yaml
mode: subagent
```

### Step 5: Continue the User Task

If the user asked to use the subagent's instructions, read the full source Markdown and follow it as task guidance. Report that the subagent was loaded from its source path.

## Expected Output

- Matched subagent name and path.
- Short metadata summary.
- Installed target status when relevant.
- Either completion of the original task using the subagent instructions, or a clear not-found result with closest candidates.
