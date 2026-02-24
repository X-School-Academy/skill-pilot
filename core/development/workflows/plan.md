# Workflow Feature Development Plan (For Approval)

Requirement reference:
- `core/development/workflows/requirement.md`

## 1. Finalized Design Decisions

1. Filename collision strategy:
   - Keep kebab-case; use numeric dash suffix: `name-2.json`, `name-3.json`, ...
2. Node data rule:
   - `Agent` requires `title`, `provider_id`, `skill`.
   - `Start` and `End` do not require node data.
3. Navigation placement:
   - Add `Workflows` as a top-level item near `Skills` (same level as `Courses`).
4. Editor implementation:
   - Use React Flow (`@xyflow/react`) for stable drag/link behavior and faster delivery.

## 2. Scope

Deliver a complete workflows feature across backend and web UI:
- Tree/list/load/create/save workflows under `core/workflows/`
- Directed-graph workflow editor (`Start`, `Agent`, `End`)
- Full save-time graph validation and error reporting
- JSON contract compliance between frontend and backend

## 3. Implementation Phases

### Phase 1: Backend workflow domain

1. Add workflow utility module in `core/engine/`:
   - safe path resolution under `core/workflows/`
   - folder tree builder and latest workflow resolver
   - filename normalization and collision-suffix resolver
   - graph validation engine returning structured errors

2. Add test coverage for utility module:
   - valid graph pass
   - cycle fail
   - orphan/reachability fail
   - degree-rule fail
   - duplicate edge/self-loop fail
   - filename format and collision behavior

### Phase 2: Backend APIs

1. Add API endpoints in `core/engine/routes.py`:
   - `GET /api/workflows/tree`
   - `GET /api/workflows/latest`
   - `GET /api/workflows/content?workflow=...`
   - `POST /api/workflows/validate`
   - `POST /api/workflows/save`

2. Save endpoint behavior:
   - validate payload shape and graph semantics
   - enforce filename rule
   - resolve filename collisions with `-N` suffix
   - persist JSON and return stored path/name

### Phase 3: WebUI route and navigation

1. Add nav item `Workflows` in:
   - `core/webui/pages/index.tsx`
   - `core/webui/pages/terminals/index.tsx` (for parity)

2. Add new page:
   - `core/webui/pages/workflows/index.tsx`

3. Implement Courses-like layout:
   - left tree nav with `New Workflow`
   - right editor panel
   - default load latest or show empty state

### Phase 4: Workflow editor

1. Canvas behaviors:
   - default nodes on create: `Start -> Agent -> End`
   - drag nodes with pointer-follow
   - connect nodes via anchors with direction arrows
   - select edge and delete by midpoint icon
   - full-height canvas and two-direction scroll

2. Agent editing:
   - title input
   - LLM provider select (default from AI & Security)
   - skill autocomplete from `/api/config/skills`

### Phase 5: Save UX and validation feedback

1. Save flow:
   - client-side shape pre-check
   - backend validate/save
   - success toast with actual saved filename

2. Error flow:
   - show aggregated validation errors
   - include rule name, node/edge identifiers, and fix hints

### Phase 6: Verification

1. Backend verification:
   - targeted API tests + validation unit tests
2. Frontend verification:
   - create/load/edit/connect/delete/save scenarios
3. Static checks:
   - `core/webui`: lint/build
   - `core/engine`: syntax/import checks for touched files

## 4. File Change Plan

- `core/engine/routes.py`
- `core/engine/workflow_editor_utils.py` (new)
- `core/webui/pages/index.tsx`
- `core/webui/pages/terminals/index.tsx`
- `core/webui/pages/workflows/index.tsx` (new)
- `core/webui/components/workflows/*` (new)
- `core/workflows/*.json` (runtime output)

## 5. Approval Gate

Approve this plan to start implementation.
