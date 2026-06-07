# Review and Evidence

Use this reference for evidence-backed architecture claims and expert review output.

## Evidence Rules

Every important architecture claim should include evidence.

Use this evidence format:

```json
{
  "claim": "The system separates request handling from business logic.",
  "confidence": "high",
  "evidence": [
    "src/routes/user.ts",
    "src/services/user-service.ts"
  ],
  "notes": "Routes call service functions instead of directly writing to the database."
}
```

Confidence levels:

```text
high: directly supported by code
medium: strongly suggested by code structure
low: possible but not proven
unknown: needs user confirmation
```

Never hide uncertainty.

If something is unclear, write:

```text
I cannot confirm this from the current files.
```

Do not claim an issue exists unless there is evidence. If the agent suspects an issue but cannot confirm it, put it in `uncertain-points.md`.

## Design and Performance Review

Review the project like an expert.

Cover:

- Architecture clarity.
- Separation of concerns.
- Coupling and cohesion.
- Data consistency.
- Error handling.
- Transaction boundaries.
- Scalability bottlenecks.
- Performance bottlenecks.
- Security risks.
- Testing gaps.
- Observability/logging gaps.
- Deployment risks.
- Maintainability risks.
- AI-agent readability.

Use this format:

| Issue | Severity | Evidence | Why it matters | Language-independent fix | Current-stack fix |
|---|---|---|---|---|---|

Severity levels:

```text
Critical
High
Medium
Low
Observation
```

## Architecture Checklist

- Is there a clear separation between interface, application logic, domain logic, and data access?
- Are components easy to name by responsibility?
- Are dependencies pointing in a healthy direction?
- Is business logic trapped inside routes/controllers/UI components?
- Are external services isolated behind adapters?

## Workflow Checklist

- Can a user action be traced from input to output?
- Are important workflows documented?
- Are background jobs visible?
- Are retries, failures, and partial success handled?

## Data Checklist

- Are the main entities clear?
- Are relationships clear?
- Are state transitions explicit?
- Are validation rules duplicated or missing?
- Are transactions handled safely?

## Performance Checklist

- Are there unnecessary loops over large data?
- Are there repeated database queries?
- Is caching used where needed?
- Are long-running jobs handled outside request paths?
- Are large files streamed instead of loaded fully into memory?

## Security Checklist

- Is authentication clear?
- Is authorization enforced near protected operations?
- Are secrets stored outside code?
- Is user input validated?
- Are file uploads safe?
- Are external API calls protected from misuse?

## Testing Checklist

- Are core workflows tested?
- Are domain rules tested separately from framework code?
- Are external services mocked?
- Are error paths tested?
- Is there a way to run tests easily?

## AI-Agent Readiness Checklist

- Can an AI agent understand the module boundaries?
- Are docs and names clear enough?
- Are tasks decomposable?
- Are there stable tests for agent changes?
- Are risky files identified?
