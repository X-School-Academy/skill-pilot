# What Is a Feature?

## Definition

A feature is a user-facing capability from the end user’s viewpoint:
- The user can see it.
- The user can operate it.

Internal functions or workflows that only help implement user-facing behavior are not features.

A feature must belong to a user story.

## Feature ownership

Features are defined by the Product Manager (or equivalent product owner role) in collaboration with key stakeholders.
Engineering and design can propose or refine feature ideas, but final definition and prioritization sit with product.

## User perspective

Software can serve different user types:
- End users: non-technical individuals using the product to accomplish tasks
- Power users: technical users who use the product within a workflow (often via CLI or configs)
- System users: other systems integrating via APIs or automation

When we discuss features, we mean user-facing capabilities, not implementation details.

Practical test:
1) The user can see it.
2) The user can operate it.

## Feature characteristics

A well-defined feature typically:
- is visible in the UI/UX (or an equivalent interface for the target user)
- is directly operable (clicks, taps, inputs, commands, API calls)
- solves a specific user need
- provides measurable value
- can be described independently
- contributes to overall product functionality

## Feature sizing and implementation scope

What counts as “one feature” depends on implementation effort and available tooling.

- Library-driven (bundled features): if a high-level library makes multiple capabilities nearly trivial to enable, they may be treated as one feature (example: using `fastmcp` where enabling `stdio`, `http`, and `sse` is largely a parameter change).
- Custom implementation (granular features): if the same capabilities must be built from scratch, each may be defined as its own feature due to meaningful design, implementation, and test effort (example: “Implement SSE Transport”).

## Reviewability and Testability

A feature must be treated as standard software development work, adhering to the following strict requirements:

- **Testable**: Every feature must include appropriate tests (unit, integration, or E2E) to verify its functionality automatically.
- **Code Reviewable**: The implementation must be structured and scoped so that a human can review the code in several minutes without significant effort.
- **Avoid "Big Bang" Changes**: Do not write large chunks of code at once. Work should be broken down to ensure it is manageable, minimizing the risk of introducing complex bugs that are hard to spot.

## Examples

### Feature examples
- User authentication: a login experience where a user enters credentials to access an account
- Product search: a search UI that finds items by name or category
- Data export: a control that downloads activity as CSV
- REST API endpoint (system user): a documented endpoint like `/api/v1/orders` returning JSON
- CLI command (power user): a command like `swarm init` that creates a new project structure
- Dark mode toggle: a setting that changes the visual theme

## Who defines whether something is a feature?

Whether something is a feature depends on the target user.

- Logging to console/file:
  - feature for power users or system users who rely on logs (debugging, monitoring, auditing)
  - not a feature for non-technical end users (it provides no direct interaction/value)

- Configuration via text files (YAML/JSON):
  - feature for power users who want “infrastructure as code,” versioning, and automation
  - not a feature for end users who expect a GUI and find raw text editing error-prone

- API rate-limiting headers:
  - feature for system users (integration developers), since headers like `X-RateLimit-Remaining` enable automated pacing
  - not a feature for end users of the main application
