# Dev Plan: Home Screen with Sidebar Navigation & Terminal Management

## Overview

Restructure the Skill Pilot web UI so the root route (`/`) becomes a Home Screen hub with sidebar navigation and embedded terminal management, while moving the existing course viewer to `/courses`.

## Steps

### Step 1: Create `pages/courses/index.tsx`

- Copy current `pages/index.tsx` to `pages/courses/index.tsx`
- Adjust all relative imports to add one `../` level (components, libs)
- Change all `router.push('/?course=...')` to `router.push('/courses?course=...')`
- Add a "Back to Home" button bar between header and content area
- Update `<title>` to "Skill Pilot - Courses"
- Remove unused imports (`IconChevronRight`, `IconChevronDown`)

### Step 2: Replace `pages/index.tsx` with Home Screen

- Use Mantine `AppShell` with `Header` (60px) + `Navbar` (240px sidebar)
- Header: logo (links to `/`) + LLM provider `Select` dropdown
- Sidebar navigation with `NavLink` + `Divider` sections:
  - Top: New Terminal, Terminals
  - Courses (navigates to `/courses`)
  - Workspace: Learning, Projects, Research, Tasks (placeholders)
  - System: Development (placeholder)
  - Commercial Project: Dev Swarm (navigates to `/dev-swarm`)
  - Processes, Skills, MCP Servers, Schedule, Extensions, Profile (placeholders)
- Main panel renders views based on `activeView` state:
  - **Home**: centered headline, subtitle, text input + Start button
  - **Terminals**: tab bar + stacked iframes (display:block/none)
  - **Placeholders**: "Coming Soon" message
- Terminal management:
  - `TerminalSession` interface: `{ id, command, label, createdAt }`
  - Create terminal: generates iframe to `/terminal?command=...`
  - Close terminal: removes from array, unmounts iframe
  - Iframes stay mounted when switching tabs to preserve WebSocket
  - Use `activeTerminalIdRef` to avoid stale closure in `closeTerminal`

### Step 3: Update Dev Swarm Page

- Change logo text from "AI Code" to "Skill Pilot" (line 1557)
- Add back-to-home `ChevronLeft` button in header (before menu icon)
- Uses existing `ChevronLeft` import

### Step 4: Code Review & Fix

- Remove unused imports from both new files
- Fix stale closure bug in `closeTerminal` using `useRef` for `activeTerminalId`
- Verify build with `npx next build`

## Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| iframe-based terminals | Preserves xterm WebSocket connections when switching tabs; existing terminal page handles resize |
| `display:none` vs unmount | Keeps terminals alive; only unmount on explicit close |
| `useState` (no Redux) | Terminal sessions are ephemeral browser-session state |
| Full-page nav for Courses/Dev Swarm | These are complex pages with their own layouts |
| Inline rendering for other views | Placeholder views are lightweight; enables future inline expansion |
| `useRef` for activeTerminalId | Prevents stale closure when closing terminals rapidly |
