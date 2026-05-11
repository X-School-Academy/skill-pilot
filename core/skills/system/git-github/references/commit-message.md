# Commit Message Drafting

Use this reference when the user asks to commit, commit changes, save changes to git, create a commit message, or review what should be committed.

## Workflow

1. Inspect Git state with `git status --short`.
2. Inspect changes with `git diff` and, if files are staged, `git diff --staged`.
3. Identify whether the changes represent one atomic task or multiple unrelated tasks.
4. Draft a Conventional Commits message for each atomic task.
5. If the user asked to commit and approval is already explicit, stage only the relevant files and commit with the selected message. Otherwise, ask before committing.

## Message Requirements

- Use Conventional Commits format: `type(scope): summary`.
- Use imperative mood in the summary, such as `Add`, `Fix`, `Refactor`, or `Update`.
- Keep the summary under 72 characters.
- Include `BREAKING CHANGE:` footer when the diff contains a breaking change.
- Keep the message focused on one logical task.

## Atomic Commit Guidance

Each commit should represent one logical change. Recommend separate commits for:

- Different change types, such as feature work and documentation.
- Different features.
- Different bug fixes.
- Different refactors.

Avoid broad messages that combine unrelated work, such as `Add feature X and fix bug Y`. Split those into focused commits when possible.

## Content to Avoid

Do not add generated-by or co-author trailers unless the user explicitly requests them.
