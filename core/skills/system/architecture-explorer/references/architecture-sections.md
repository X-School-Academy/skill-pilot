# Architecture Sections

Use this reference for the content and wording rules for the main Architecture Explorer sections.

## Executive Summary

Explain the project in simple words:

- What the project does.
- Who uses it.
- What inputs it receives.
- What outputs it produces.
- What the main runtime flow looks like.
- What the most important modules are.

Avoid implementation-heavy wording in this section.

Good wording:

```text
This system receives user requests, validates them, runs business rules, stores state, and returns results through an API.
```

Avoid wording like:

```text
This FastAPI app uses Pydantic models and SQLAlchemy sessions.
```

That belongs in the tech stack section.

## Language-Independent Architecture

This is the most important section.

Describe the system using neutral software design concepts:

- System responsibilities.
- Domain concepts.
- Components.
- Data entities.
- Commands and queries.
- Workflows.
- State transitions.
- External dependencies.
- User roles.
- Error handling model.
- Configuration model.
- Persistence model.
- Communication model.

Use language-independent terms such as:

```text
Request Handler
Application Service
Domain Service
Repository
Data Store
Message Queue
Scheduler
Worker
External API Adapter
Authentication Boundary
Authorization Rule
Validation Layer
Persistence Boundary
Presentation Layer
```

Do not use language-specific names as the main architectural concepts unless they are essential.

Bad:

```text
The Express router calls the Prisma client.
```

Good:

```text
The API request handler calls the data access layer to read and write persistent records.
The current implementation uses Express for routing and Prisma for database access.
```

## Current Tech Stack and Implementation Details

This is the only section where technology-specific details should be central.

Include:

- Programming language.
- Frameworks.
- Libraries.
- Package manager.
- Build system.
- Test framework.
- Database.
- API style.
- Frontend framework.
- Backend framework.
- Deployment tools.
- Environment variables.
- External services.

Explain what each technology is responsible for, then map each technology back to the language-independent architecture.

Example:

```text
FastAPI: Implements HTTP API request handling.
PostgreSQL: Stores persistent application data.
Redis: Stores short-lived cache/session/job state.
React: Implements the browser-based user interface.

FastAPI = Request Handler Layer
SQLAlchemy = Data Access Layer
PostgreSQL = Persistent Data Store
Celery = Background Worker System
```

## Module Map

Create a module map that explains:

- File/folder structure.
- Responsibility of each major folder.
- Main entry points.
- Main internal modules.
- Which modules call which other modules.
- Which modules should not depend on each other.

Use a table:

| Module / Folder | Language-independent role | Current implementation detail | Evidence | Notes |
|---|---|---|---|---|
| `api/` | Request handling boundary | HTTP routes/controllers | file paths | Receives external requests |
| `services/` | Application/business logic | Service classes/functions | file paths | Coordinates workflows |
| `models/` | Domain/data model | ORM/schema classes | file paths | Defines persistent data |

## Core Workflows

Identify the most important workflows in the system.

For each workflow, describe:

- Trigger.
- Input.
- Main steps.
- Decision points.
- Data read/write operations.
- External service calls.
- Output.
- Error cases.
- Relevant files.

Use this format:

```text
Workflow: User creates an item

Trigger:
- User submits a create request.

Language-independent flow:
1. Request handler receives input.
2. Validation layer checks required fields.
3. Application service applies business rules.
4. Repository writes the new record.
5. Response mapper returns the created result.

Current implementation:
- Route file: ...
- Service file: ...
- Model file: ...

Possible issues:
- Validation may be duplicated.
- No transaction boundary is visible.
- Error handling may leak internal details.
```

## Interface and Boundary Map

Identify all important system boundaries:

- User interface boundary.
- API boundary.
- Authentication boundary.
- Authorization boundary.
- Validation boundary.
- Database boundary.
- External API boundary.
- File system boundary.
- Queue/job boundary.
- AI/LLM boundary if present.
- Payment boundary if present.
- Notification boundary if present.

For each boundary:

```text
Boundary: External API Adapter
Purpose: Keeps third-party service logic separate from internal business logic.
Current implementation: ...
Evidence: ...
Risk: API-specific code may be leaking into core business logic.
Remake rule: Keep this as an adapter/interface in any target language.
```

## Data Model

Explain the data model in language-independent terms.

Include:

- Main entities.
- Entity relationships.
- Ownership rules.
- Lifecycle/state transitions.
- Required fields.
- Derived fields.
- Data validation rules.
- Data persistence rules.

Separate:

```text
Conceptual data model
vs
Database/schema implementation
```

Example:

```text
Conceptual entity: Course
Purpose: Represents a learning path selected or created by a user.
Important fields: title, sections, status, owner, progress.
Lifecycle: draft -> active -> completed -> archived.
Current implementation: Strapi collection type / SQL table / JSON file / ORM model.
```

## Runtime and Deployment View

Explain how the system runs:

- Main process.
- Worker process.
- Scheduler process.
- Database.
- Cache.
- Queue.
- Static assets.
- Build step.
- Environment variables.
- External dependencies.
- Deployment target.

Keep this mostly language-independent, then add current implementation details.

Example:

```text
Language-independent runtime:
- Web server receives API requests.
- Background worker processes long-running jobs.
- Database stores persistent records.
- Object storage stores generated files.

Current implementation:
- Web server: Node.js / FastAPI / Django / etc.
- Worker: Celery / BullMQ / custom script / etc.
```

## Remake Guide

This section helps the user instruct another AI to rebuild the project in another coding language.

Include:

- What must be preserved.
- What can be changed.
- Language-independent module list.
- API contract.
- Data model contract.
- Workflow contract.
- Error behavior contract.
- Security/auth rules.
- Performance expectations.
- Suggested implementation phases.
- Test plan.

Use this format:

```text
Remake goal:
Rebuild this project in <target language/framework> while preserving the same core workflows and behavior.

Must preserve:
- User-facing behavior.
- Core domain entities.
- API contract.
- Data lifecycle.
- Auth rules.
- Important background jobs.

Can change:
- File structure.
- Framework-specific routing style.
- ORM library.
- UI component library.
- Internal helper function names.

Language-independent architecture to implement:
1. Presentation Layer
2. Request Handler Layer
3. Application Service Layer
4. Domain Logic Layer
5. Data Access Layer
6. External Service Adapter Layer
7. Background Worker Layer
```

Also include a prompt the user can give to an AI coding agent:

```text
You are rebuilding an existing project from a language-independent architecture spec.
Do not copy the original implementation style blindly.
Preserve the behavior, workflows, data model, and interfaces.
Use the target stack idiomatically.
Before coding, create a module plan, API contract, data model, and test plan.
```

## Learning Guide

Create a learning guide for users who want to understand the project.

Include:

- Beginner explanation.
- Important concepts to learn first.
- Suggested reading order for files.
- Tasks for exploring the codebase.
- Questions to ask AI.
- Small remake exercises.
- Debugging exercises.
- Design review exercises.

Example tasks:

```text
Task 1: Trace one request from user input to database write.
Task 2: Draw the data flow for one workflow.
Task 3: Replace one external service with a mock adapter.
Task 4: Rewrite one small module in another language.
Task 5: Identify one design issue and propose a fix.
```
