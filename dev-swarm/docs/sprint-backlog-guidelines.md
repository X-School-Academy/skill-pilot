# AI-Driven Development Sprint and Backlog Guidelines

## Purpose

This guideline defines a workflow designed for AI-driven development.

Goals:
- Treat AI as the primary builder.
- Ensure every iteration results in a tangible, demoable product.

## Backlog guidelines

Each backlog item is a feature.

### Definition
- A backlog item is a user-facing capability (example: “Allow users to log in with Google”).
- Use the “What is a Feature?” definition (`./what-is-a-feature.md`).
- **Testable**: Must be verifiable via automated tests (unit, integration, or E2E) and from the user’s perspective.
- **Reviewable**: The implementation must be easy for a human to review in several minutes. It must be treated as normal code development.
- **Atomic**: Avoid large chunks of code. Keep changes small to ensure high-quality human review.

### Backlog types
Each backlog item should be one of the following:
- A small slice of the sprint feature, or
- A step in the sprint feature that a user can take, or
- A small, user-visible and user-testable feature.

### How to split a sprint into backlogs
Start with the user story.

Ask: “If I’m a user, what are the steps I take?”

Example journey for “Register a DNS domain”:
- Check domain availability.
- Register the domain.
- See it in my domain list.

Convert each step into a backlog item.

## Sprint guidelines

A sprint is a committed scope of work that results in a verifiable milestone.

### Sprint definition
- Selected backlogs should form a cohesive narrative (example: “User Authentication Sprint”).
- A sprint can be defined as a user story.
- The first sprint must produce a working mini product (a “Hello World” experience).
- Every sprint after that adds value without breaking what already works.

### Sprint outcome: the cumulative increment
- Demoable: the output is not just merged code; it is an updated version of the application.
- End-user ready: focus on product evolution, not only unit tests.
- Review: walk through the updated product to verify new features in context.

## Summary
- Backlog = feature (end-to-end implementation).
- Sprint = cumulative milestone (progressive product evolution).
- AI = builder (executes the full-stack implementation).
