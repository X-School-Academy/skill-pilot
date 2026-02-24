# SKILL.md Normalization Checklist

Use this after importing the skill folder.

## 1) Frontmatter checks

- `name` matches the directory name exactly
- `name` is lowercase, digits/hyphens only, no leading/trailing hyphen
- `description` explains what the skill does and when to use it
- Keep `description` under 1024 characters
- Add optional `compatibility` only when it adds real constraints

## 2) Required body sections

Ensure these exist:

- `# AI Builder - <Skill Title>`
- `## When to Use This Skill`
- `## Your Roles in This Skill`
- `## Role Communication`
- `## Instructions`

## 3) Role communication format

Include this exact pattern:

`As a {Role, and Role-XYZ if have more roles}, I will {action description}`

## 4) Instruction quality

- Steps are actionable and ordered
- Any risky operations require explicit user confirmation
- Commands are concrete and copyable
- References are linked via relative paths

## 5) Keep concise

- Keep `SKILL.md` focused
- Move detailed or branching logic into `references/`
- Prefer direct prompt + text instructions over adding helper scripts
