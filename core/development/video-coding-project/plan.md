# Video Coding Project Development Plan (For Approval)

Requirement reference:
- `core/development/video-coding-project/requirement.md`

## 1. Requirement Review

The updated requirement expands the original rename/adaptation request into three concrete deliverables:

1. Replace the current `Projects` navigation entry with `Vibe Coding`, pointing to a Vibe Coding workspace UI instead of the existing generic Projects view.
2. Build a Vibe Coding experience derived from the Tasks feature, but with:
   - project-oriented wording
   - workspace root `workspace/vibe-coding/`
   - fixed lifecycle files per project
   - filename-specific action buttons and prompts
3. Add a new family of system skills named `vibe-coding-project-*`, with explicit first-pass behavior for:
   - `vibe-coding-project-create`
   - `vibe-coding-project-initial`
   - `vibe-coding-project-deploy`

## 2. Current Code Review and Gap Analysis

### Existing implementation

1. The repo already has a working Tasks feature:
   - frontend page: `core/webui/pages/tasks/index.tsx`
   - backend routes: task tree/content/save/create/delete/file endpoints in `core/engine/routes.py`
   - workspace root constant: `TASKS_DIR` in `core/engine/settings.py`
2. Navigation is defined in multiple places:
   - `core/webui/components/main-layout.tsx`
   - `core/webui/pages/index.tsx`
   - `core/webui/pages/terminals/index.tsx`
3. System skills live under `core/skills/system/`, and there is currently no `vibe-coding-project-*` skill set.

### Gaps against the requirement

1. There is no `workspace/vibe-coding/` backend domain, constant, or API surface.
2. The current Tasks create flow is file-first; the requirement needs a project-first flow with fixed filenames and multiple modal actions.
3. The current Tasks page exposes one generic `Execute` action; the requirement needs filename-aware actions:
   - `requirements.md`: `Refine`, `Initial`, `Plan`
   - `plan.md`: `Implement`
   - `implement.md`: `Review`, `Test`, `Deploy`
   - `update.md`: `Update Code`
   - `issues.md`: `Fix Issues`
4. Current delete behavior only removes the selected file and deletes the parent folder only if it becomes empty. The requirement adds a special destructive rule for deleting `requirements.md`: remove the entire project folder after an explicit `delete` confirmation.
5. The current nav label `Projects` appears in multiple UI entry points, so this is not a single-file rename.
6. The required system skills do not exist yet, and some of them imply integration with external systems:
   - GitHub repository initialization
   - AWS EC2 deployment

## 3. Finalized Planning Decisions

1. Create a dedicated Vibe Coding route instead of overloading `/tasks`.
   - Proposed route: `core/webui/pages/vibe-coding/index.tsx`
2. Keep the current Tasks feature intact.
   - Vibe Coding should reuse proven logic conceptually, but remain a separate feature because the workspace rules, labels, create flow, and action matrix are materially different.
3. Add a parallel backend API surface for Vibe Coding instead of mutating `/api/tasks/*`.
   - This reduces regression risk for existing Tasks users.
4. Keep the first implementation focused on markdown/text project files under the fixed lifecycle names.
   - The plan will preserve generic text-file support where already natural, but priority goes to the required five files and their flows.
5. Treat the new system skills as scaffolded, usable first versions.
   - They should be valid system skills with clear instructions, but the requirement already states they will be refined later.

## 4. Implementation Phases

### Phase 1: Backend Vibe Coding workspace domain

1. Add a Vibe Coding workspace constant in `core/engine/settings.py`.
   - `VIBE_CODING_DIR = PROJECT_DIR / "workspace" / "vibe-coding"`
2. Extract or duplicate the task-path helpers in `core/engine/routes.py` into Vibe Coding equivalents.
3. Implement Vibe Coding-safe path handling for:
   - project folders under `workspace/vibe-coding/`
   - fixed files inside each project folder
   - text/media type detection where reused
4. Add backend helpers for project naming:
   - kebab-case normalization for project folders
   - duplicate suffix strategy `_1`, `_2`, ... as required

### Phase 2: Backend Vibe Coding APIs

1. Add new endpoints in `core/engine/routes.py` for the Vibe Coding workspace:
   - `GET /api/vibe-coding/tree`
   - `GET /api/vibe-coding/latest`
   - `GET /api/vibe-coding/content`
   - `POST /api/vibe-coding/save`
   - `POST /api/vibe-coding/create-project`
   - `POST /api/vibe-coding/create-update-request`
   - `POST /api/vibe-coding/create-issue-report`
   - `POST /api/vibe-coding/delete`
   - `GET /api/vibe-coding/file`
2. Ensure project creation writes `requirements.md` directly from the modal input.
3. Ensure update requests append or replace `update.md` intentionally and consistently.
4. Ensure issue reports append or replace `issues.md` intentionally and consistently.
5. Implement special deletion behavior:
   - deleting `requirements.md` removes the entire project folder
   - non-requirement files keep standard file deletion behavior

### Phase 3: WebUI navigation and route wiring

1. Replace the `Projects` nav label with `Vibe Coding` in all current nav definitions:
   - `core/webui/components/main-layout.tsx`
   - `core/webui/pages/index.tsx`
   - `core/webui/pages/terminals/index.tsx`
2. Point those entries to the new Vibe Coding page rather than `/?view=projects`.
3. Add `core/webui/pages/vibe-coding/index.tsx`.
4. Preserve the overall Tasks page layout and behavior patterns:
   - left file tree
   - right content/editor area
   - latest-item bootstrapping
   - sidebar resizing

### Phase 4: Vibe Coding page behavior

1. Adapt the Tasks page logic for Vibe Coding terminology and APIs:
   - `Tasks` -> `Projects`
   - task folder selection -> project selection
   - task file actions -> lifecycle-aware project file actions
2. Replace the `Add Task` flow with a `New` menu/modal supporting:
   - `New Project`
   - `Update Request`
   - `Bug/Issue Report`
3. Implement current-project defaults for update and issue flows.
4. Support fixed-file conventions under each project:
   - `requirements.md`
   - `plan.md`
   - `implement.md`
   - `update.md`
   - `issues.md`
5. Preserve general text-file editing behavior for compatible files.

### Phase 5: File-specific action buttons and session prompts

1. Add a filename-to-actions mapping on the Vibe Coding page.
2. Replace the generic `Execute` button with required action buttons per filename.
3. Generate exact prompt strings from the requirement for each action.
4. Reuse the existing new-session redirect pattern from the Tasks page so each button:
   - constructs the prompt
   - opens a new session
   - includes the project-relative file reference
5. Add destructive confirmation UI for deleting `requirements.md`.
   - Require manual entry of `delete`

### Phase 6: System skill scaffolding

1. Create new system skill directories under `core/skills/system/` for the first-pass skill set:
   - `vibe-coding-project-create`
   - `vibe-coding-project-refine`
   - `vibe-coding-project-initial`
   - `vibe-coding-project-plan`
   - `vibe-coding-project-implement`
   - `vibe-coding-project-review`
   - `vibe-coding-project-test`
   - `vibe-coding-project-deploy`
   - `vibe-coding-project-update`
   - `vibe-coding-project-fix-issues`
2. Write valid `SKILL.md` files for each.
3. Define first-pass behavior explicitly:
   - `create`: create `workspace/vibe-coding/{project-name}/requirements.md` from a prompt
   - `initial`: initialize a GitHub-backed project workflow
   - `deploy`: deploy to AWS EC2
4. Keep these skills instruction-heavy first, and avoid overcommitting to automation not yet supported in the codebase.
5. Reuse or reference existing system skills where appropriate:
   - GitHub-related workflows
   - AWS/EC2-related workflows
   - agent-skill creation conventions

### Phase 7: Verification

1. Backend verification:
   - validate project creation naming and duplicate suffix behavior
   - verify fixed file writes
   - verify delete rules for `requirements.md`
   - verify tree/latest/content/file responses
2. Frontend verification:
   - nav opens Vibe Coding from all entry points
   - new project flow creates a project and opens `requirements.md`
   - update request flow targets the selected/default project
   - issue report flow targets the selected/default project
   - filename-specific action buttons render correctly
   - action buttons redirect with the expected prompts
3. Skill verification:
   - confirm all new skills are discoverable and structurally valid

## 5. File Change Plan

Expected primary changes:

- `core/engine/settings.py`
- `core/engine/routes.py`
- `core/webui/components/main-layout.tsx`
- `core/webui/pages/index.tsx`
- `core/webui/pages/terminals/index.tsx`
- `core/webui/pages/vibe-coding/index.tsx` (new)
- `core/skills/system/vibe-coding-project-create/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-refine/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-initial/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-plan/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-implement/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-review/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-test/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-deploy/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-update/SKILL.md` (new)
- `core/skills/system/vibe-coding-project-fix-issues/SKILL.md` (new)

Possible refactor candidates if needed during implementation:

- shared helpers extracted from `core/webui/pages/tasks/index.tsx`
- shared backend tree/path utilities extracted from `core/engine/routes.py`

## 6. Open Questions

1. None required to draft the first implementation plan.
2. During implementation, one decision may need confirmation if ambiguity appears:
   - whether `update.md` and `issues.md` should overwrite existing content or append new entries

## 7. Approval Gate

Approve this plan to start implementation.
