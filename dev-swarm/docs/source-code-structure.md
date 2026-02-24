# Source Code Structure Guidelines

This guide provides general guidelines for organizing the `{SRC}/` folder structure in projects.

## Goal

Give AI developers a consistent, searchable map for where code lives and how to add new code in `{SRC}/`.

## Structure Strategies

Choose a primary organization strategy based on project needs:

### Option A: Layer-Based (Traditional)

Best for: Simple projects, single-team ownership, clear separation of concerns.

```
{SRC}/
├── controllers/    # HTTP request handlers
├── services/       # Business logic
├── models/         # Data models
├── utils/          # Utilities
└── tests/          # Tests
```

### Option B: Modular/Domain-Based

Best for: Medium-large projects, multiple teams, feature isolation.

```
{SRC}/
├── auth/           # Authentication module
├── users/          # User management module
├── payments/       # Payment module
├── shared/         # Shared code
└── tests/          # Integration tests
```

### Option C: Monorepo

Best for: Projects with distinct frontend/backend, micro services, or multiple deployment targets.

```
{SRC}/
├── frontend/
│   ├── components/
│   ├── pages/
│   └── shared/
├── backend/
│   ├── api/
│   ├── services/
│   └── database/
└── services/
    ├── cpu-video-processor/
    └── gpu-video-generator/
```

### Option D: Simple Flat Structure (Small Projects)

Best for: Scripts, small utilities, prototypes.

```
{SRC}/
├── main.py
├── utils.py
├── config.py
└── tests/
```

## Naming Conventions

Define and follow these for your project:

1. **File naming rules**
   - Use consistent case (kebab-case, camelCase, or snake_case)
   - Choose meaningful, descriptive names

2. **Test naming rules**
   - Examples: `.test.*`, `.spec.*`, `test_*`, `*_test.*`

3. **Type/contract naming rules**
   - Examples: `.types.ts`, `.d.ts`, `_types.py`

## Placement Rules

Establish where new code should live:

1. **New feature code** - In appropriate module or feature directory
2. **Shared utilities** - In `shared/`, `utils/`, or `common/` directory
3. **API contracts/schemas/DTOs** - Near the API layer or in dedicated contracts folder
4. **UI components** - In `components/` directory (frontend)
5. **Backend services** - In `services/` directory

## Tests Location

Choose one approach:

- **Co-located**: Tests next to source files (`foo.ts` + `foo.test.ts`)
- **Separate**: Tests in dedicated `tests/` or `__tests__/` directory
- **Hybrid**: Unit tests co-located, integration/e2e tests separate

## Entry Points

Document your entry points clearly:

- Main entry files: `{SRC}/main.ts`, `{SRC}/index.ts`, `{SRC}/server.ts`, `{SRC}/app.py`
- Where routing or application bootstrapping happens
- CLI entry points if applicable

## Constraints

- Keep the structure as simple as possible while meeting requirements
- Align to the approved tech stack
- Support feature-driven development pattern
- Update `{SRC}/README.md` when structure changes

## Checklist

When setting up or reviewing source code structure:

- [ ] Structure strategy is clearly chosen and documented
- [ ] Naming conventions are explicit and followed
- [ ] Placement rules cover common additions
- [ ] Test file locations are defined
- [ ] Entry points are documented
- [ ] Examples show where to add new files