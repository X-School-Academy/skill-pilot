# Feature Retrieval Index: WebUI Next.js Frontend

## Retrieval Keywords

webui, Next.js, frontend, web UI, React, pnpm, TypeScript, Next.js pages, web interface, skill-pilot-webui, webui dev, webui build, webui start, _app.tsx, _document.tsx, main-layout, layout, Redux, store, components, styles, public assets

## Scope

- Next.js web application serving the Skill Pilot UI
- Page routing under `core/webui/pages/`
- Shared components and layouts
- Redux store for state management
- Excludes: individual page features (each has own feature file)

## Main Behavior

- Next.js app with pages router
- Dev mode: `pnpm dev` in `core/webui/`
- Production build: `pnpm build && pnpm start`
- Dev session managed via tmux as `sp-webui-dev`
- `_app.tsx` is the app shell wrapping all pages with providers
- `main-layout.tsx` provides the primary navigation layout
- Redux store in `core/webui/store/`
- Shared components in `core/webui/components/`
- API calls proxy to the engine backend

## Code Map

- `core/webui/pages/_app.tsx` — Next.js app entry
- `core/webui/pages/_document.tsx` — HTML document customization
- `core/webui/components/main-layout.tsx` — main navigation layout
- `core/webui/components/layout.tsx` — page layout wrapper
- `core/webui/store/` — Redux store
- `core/webui/components/` — shared UI components: `FileManagerContent.tsx`, `ModalDialog.tsx`, `TerminalHistoryViewer.tsx`, `EmbeddedSessionPanel.tsx`, `blocks/`, `explore/`
- `core/webui/styles/` — CSS/SCSS styles
- `core/webui/types/` — TypeScript type definitions
- `core/webui/libs/` — utility libraries
- `core/webui/public/` — static assets
- `core/webui/www/` — additional web assets
- `core/webui/scripts/` — build scripts
- `core/webui/features/` — Redux feature slices: `user/`, `assignment/`, `apiServerToken/`
- `core/skills/system/skill-pilot-webui/` — webui system skill

## Search Commands

```bash
find core/webui/pages/ -name "index.tsx" | head -20
find core/webui/components/ -type f -name "*.tsx"
find core/webui/store/ -type f
cat core/webui/pages/_app.tsx | head -40
```

## Related Features

- `core/features/engine-backend-fastapi.md`
- `core/features/codeware-dev-mode.md`
- `core/features/auth-session.md`

## Update Notes

- Package manager is `pnpm`; do not use npm or yarn
- Next.js version pinned in `core/webui/package.json`; check before major upgrades
- `core/webui/.next/` is the build output; never commit this directory
