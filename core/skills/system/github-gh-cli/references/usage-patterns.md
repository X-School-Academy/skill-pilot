# Usage Patterns

Use this reference after `gh` is installed and authenticated.

## Command selection

Prefer direct subcommands when possible:

- Repositories: `gh repo ...`
- Pull requests: `gh pr ...`
- Issues: `gh issue ...`
- Releases: `gh release ...`
- Actions: `gh run ...`, `gh workflow ...`
- Gists: `gh gist ...`
- Auth and account checks: `gh auth ...`

Use `gh api` when:

- The task needs an endpoint that is not well covered by a first-class subcommand
- You need a custom REST or GraphQL request
- You need precise field selection, pagination, or endpoint-specific behavior

## Practical patterns

Inspect repo state:

```bash
gh repo view OWNER/REPO
gh repo view OWNER/REPO --json name,description,defaultBranchRef,url
```

List or inspect pull requests:

```bash
gh pr list --repo OWNER/REPO
gh pr view 123 --repo OWNER/REPO --json title,state,author,mergeable,reviewDecision
```

Create or edit a pull request:

```bash
gh pr create --repo OWNER/REPO --title "..." --body "..."
gh pr edit 123 --repo OWNER/REPO --title "..." --body "..."
```

Work with issues:

```bash
gh issue list --repo OWNER/REPO
gh issue view 456 --repo OWNER/REPO --json title,state,labels,assignees
gh issue create --repo OWNER/REPO --title "..." --body "..."
```

Inspect workflow runs:

```bash
gh run list --repo OWNER/REPO
gh run view RUN_ID --repo OWNER/REPO --log
gh workflow run ci.yml --repo OWNER/REPO
```

Releases:

```bash
gh release list --repo OWNER/REPO
gh release view TAG --repo OWNER/REPO
```

## API usage

REST:

```bash
gh api repos/OWNER/REPO
gh api repos/OWNER/REPO/pulls --paginate
gh api repos/OWNER/REPO/issues --method POST -f title='Bug report' -f body='...'
```

GraphQL:

```bash
gh api graphql -f query='
  query($owner:String!, $name:String!) {
    repository(owner:$owner, name:$name) {
      name
      url
      pullRequests(first: 5, states: OPEN) {
        nodes { number title url }
      }
    }
  }' -F owner=OWNER -F name=REPO
```

## Output shaping

Prefer machine-readable output when the result feeds later reasoning or shell steps:

```bash
gh pr view 123 --repo OWNER/REPO --json title,body,url
gh pr list --repo OWNER/REPO --json number,title,headRefName --jq '.[] | [.number, .title] | @tsv'
gh api repos/OWNER/REPO/pulls --paginate --jq '.[].number'
```

## Execution guidance

- Use `--repo OWNER/REPO` when outside the target repository to avoid ambiguous context
- Read before write unless the user already made the desired mutation explicit
- Avoid destructive operations like closing, deleting, merging, or editing unless the user requested them
- If the task is better served by local git plus `gh`, use both deliberately and explain the split
- If the required endpoint or flag is uncertain, inspect `gh <subcommand> --help` before guessing
