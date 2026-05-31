# Find and Dynamically Use Agent Skill

Use this reference only when:

- the user asks to find and use an agent skill, but it is not installed in the active skill list
- the user asks for an agent skill that cannot be found in the active installed skills

This flow lets the agent dynamically load a skill from project skill folders without requiring that skill to be configured in the active skill list.

## Skill Folders

Search these four folders:

- `core/skills/user/`
- `dev-swarm/skills/`
- `core/skills/system/`
- `core/skills/third-party/`

Do not search ignored paths. Respect any ignore file that applies to the repository.

## Steps

### Step 1: Search Potential Skill Folders

Use `rg` first where possible. Search folder names and metadata/content for the user-mentioned skill name or partial name.

Useful commands:

```bash
rg --files core/skills/user dev-swarm/skills core/skills/system core/skills/third-party -g 'SKILL.md'
```

```bash
rg -n "<skill-name-or-keyword>" core/skills/user dev-swarm/skills core/skills/system core/skills/third-party -g 'SKILL.md'
```

If `rg` is unavailable, use `find` and `grep`:

```bash
find core/skills/user dev-swarm/skills core/skills/system core/skills/third-party -name SKILL.md
```

```bash
grep -RIn "<skill-name-or-keyword>" core/skills/user dev-swarm/skills core/skills/system core/skills/third-party --include SKILL.md
```

### Step 2: Inspect Candidate Metadata

For each candidate `SKILL.md`, extract frontmatter metadata with:

```bash
sed -n '2,/^---$/p' <candidate-skill-folder>/SKILL.md | sed '$d'
```

Read only enough metadata to decide whether the skill is likely correct:

- `name`
- `description`
- any relevant selection metadata

### Step 3: Choose the Correct Skill

Select the candidate whose `name` or `description` best matches the user's requested skill or task.

If multiple candidates match, prefer:

1. exact skill name match
2. exact folder name match
3. strongest description match for the requested task
4. user/category-specific skill over broader system or third-party alternatives when the user intent is personal/project-specific

If no candidate clearly matches, report that the skill was not found and list the closest candidate names.

### Step 4: Load the Skill as a Normal Agent Skill

If the candidate is correct, read its full `SKILL.md`.

Treat the loaded `SKILL.md` as the active skill instructions for the user's task:

- follow its trigger rules and workflow
- open only the reference files it explicitly routes to
- resolve referenced relative paths from that skill folder
- use its scripts or assets when instructed
- report that the skill was dynamically loaded from its folder

### Step 5: Continue the User Task

After loading the matched skill, continue the original task using that skill. Do not stop after discovery unless the user only asked to find the skill.

## Expected Output

- The matched skill name and folder path.
- A short metadata summary.
- Either completion of the original task using the dynamically loaded skill, or a clear not-found result with closest candidates.
