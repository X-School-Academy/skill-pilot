# Platform Shell And Navigation

## Brief

Shared Skill Pilot app shell with the main sidebar, grouped navigation, header branding, and active-route behavior.

## User Value

- Gives one stable entry point across the product.
- Organizes features by workspace, commercial project, and admin areas.
- Keeps navigation consistent across desktop and mobile layouts.

## Main Behavior

- Renders the left navigation with grouped sections such as `Workspace`, `Skill Pilot`, `Commercial Project`, and `Skills`.
- Highlights the active page or active `/?view=` home sub-view.
- Shows the Skill Pilot logo and the global LLM provider selector in the header.
- Uses a collapsible burger menu on small screens.

## Related Features

- `new-session.md`
- `live-sessions.md`
- `learning.md`
- `vibe-coding.md`
- `research.md`
- `tasks.md`
- `skill-pilot-development.md`
- `dev-swarm.md`

## Code References

- `core/webui/components/main-layout.tsx`
- `core/webui/pages/index.tsx`
- Component names: `MainLayout`, `NAV_ITEMS`
- Keywords: `dividerBefore`, `view`, `isActive`, `router.push`, `llm/providers`

