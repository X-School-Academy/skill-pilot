# Project Naming Procedure

Determine the project name in this priority order:

1. First priority: use the title from `{SRC}/README.md` if it exists
2. Second priority: use the title from `00-init-ideas/README.md` if it exists
3. Third priority: use the title from the repo root `README.md` if it exists
4. If none exist: ask the user to provide a project name

Extract the title from the first `# Title` or `## Title` heading in these files.