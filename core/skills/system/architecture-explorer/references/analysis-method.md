# Analysis Method

Use this reference to analyze a project before producing architecture conclusions.

## Step 1: Project Inventory

Inspect:

- README.
- Package files.
- Build files.
- Config files.
- Environment examples.
- Docker files.
- CI/CD files.
- Source directories.
- Test directories.
- Database migration/schema files.
- API route files.
- UI route files.
- Worker/scheduler files.

Create a basic inventory before drawing conclusions.

## Step 2: Entry Point Discovery

Find:

- Application startup entry point.
- Main API/router entry point.
- Frontend entry point.
- CLI entry point.
- Worker entry point.
- Scheduler entry point.
- Test entry point.

Explain how execution begins.

## Step 3: Component Discovery

Group files into language-independent components:

```text
Presentation Layer
Request Handler Layer
Application Service Layer
Domain Logic Layer
Data Access Layer
External Adapter Layer
Background Worker Layer
Configuration Layer
Testing Layer
Deployment Layer
```

Do not depend on the original folder names too much. Infer responsibility from behavior.

## Step 4: Workflow Tracing

Trace at least three important workflows if possible.

For each workflow:

1. Start from an external trigger.
2. Follow function/module calls.
3. Identify data read/write operations.
4. Identify external service calls.
5. Identify output.
6. Identify error paths.

## Step 5: Data Model Extraction

Find:

- Database tables.
- ORM models.
- JSON schemas.
- Type definitions.
- Validation models.
- API request/response models.
- State enums.
- Domain concepts.

Then convert them into a conceptual data model.

## Step 6: Diagram Generation

Generate Mermaid diagrams only after understanding the architecture.

Do not create diagrams from file names alone.

Each diagram should include a short explanation and file evidence.

Validate diagrams for Mermaid syntax where possible.

## Step 7: Expert Review

Evaluate:

- Whether the architecture is understandable.
- Whether business logic is mixed with framework code.
- Whether data access is isolated.
- Whether workflows are testable.
- Whether error handling is consistent.
- Whether performance bottlenecks exist.
- Whether external dependencies are isolated.
- Whether the project is easy for an AI coding agent to modify.

## Step 8: Remake Abstraction

Extract the design into a remake-ready spec.

The remake spec should avoid current-stack assumptions unless they are required.

Bad:

```text
Use Django models with foreign keys exactly like the original SQLAlchemy models.
```

Good:

```text
Create persistent entities for User, Project, Task, and Result.
Project belongs to User.
Task belongs to Project.
Result belongs to Task.
Use the target framework's normal persistence mechanism.
```
