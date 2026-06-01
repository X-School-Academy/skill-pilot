# Mermaid Diagrams

Use this reference to create architecture diagrams after understanding the project workflows and boundaries.

## Diagram Rules

- Generate Mermaid diagrams for the architecture.
- Prefer language-independent labels first.
- Add current implementation details in parentheses only when useful.
- Do not create diagrams from file names alone.
- Each diagram should include a short explanation and file evidence.
- Validate diagrams for Mermaid syntax where possible.

## Preferred Diagram Types

1. `flowchart TD` for component maps.
2. `sequenceDiagram` for request workflows.
3. `classDiagram` for domain model relationships when useful.
4. `erDiagram` for database entities.
5. `C4Context` or C4-style flowchart for system context if Mermaid C4 is not available.

## Generic Component Example

```mermaid
flowchart TD
    User[User]
    UI[Presentation Layer]
    API[Request Handler Layer]
    Service[Application Service]
    Domain[Domain Logic]
    Repo[Data Access Layer]
    DB[(Persistent Data Store)]
    External[External Service]

    User --> UI
    UI --> API
    API --> Service
    Service --> Domain
    Service --> Repo
    Repo --> DB
    Service --> External
```

If useful, add current implementation details in parentheses:

```text
Request Handler Layer (FastAPI routes)
Data Access Layer (SQLAlchemy repositories)
```

## System Context Template

```mermaid
flowchart TD
    User[User]
    System[Software System]
    DataStore[(Persistent Data Store)]
    ExternalService[External Service]

    User --> System
    System --> DataStore
    System --> ExternalService
```

## Component Map Template

```mermaid
flowchart TD
    UI[Presentation Layer]
    API[Request Handler Layer]
    App[Application Service Layer]
    Domain[Domain Logic]
    Repo[Data Access Layer]
    DB[(Persistent Data Store)]
    Adapter[External Service Adapter]
    Worker[Background Worker]

    UI --> API
    API --> App
    App --> Domain
    App --> Repo
    Repo --> DB
    App --> Adapter
    Worker --> App
```

## Main Workflow Sequence Template

```mermaid
sequenceDiagram
    actor User
    participant UI as Presentation Layer
    participant API as Request Handler
    participant Service as Application Service
    participant Domain as Domain Logic
    participant Repo as Data Access Layer
    participant DB as Persistent Data Store

    User->>UI: Perform action
    UI->>API: Send request
    API->>Service: Validate and delegate
    Service->>Domain: Apply business rules
    Service->>Repo: Read/write data
    Repo->>DB: Persist data
    DB-->>Repo: Return result
    Repo-->>Service: Return entity
    Service-->>API: Return application result
    API-->>UI: Return response
    UI-->>User: Show result
```

## Data Flow Template

```mermaid
flowchart LR
    Input[Input]
    Validate[Validation]
    Transform[Transformation]
    BusinessRules[Business Rules]
    Persist[(Persistence)]
    Output[Output]

    Input --> Validate
    Validate --> Transform
    Transform --> BusinessRules
    BusinessRules --> Persist
    BusinessRules --> Output
```
