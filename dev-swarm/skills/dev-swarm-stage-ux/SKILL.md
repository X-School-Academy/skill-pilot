---
name: dev-swarm-stage-ux
description: Design the user experience including visual design system, wireframes, user flows, responsive guidelines, and accessibility requirements. Use when starting stage 06 (ux) or when user asks about UI design, wireframes, or design system.
---

# Stage 06 - UX Design

Design the user experience including visual design system, wireframes, user flows, responsive guidelines, and accessibility requirements to create a cohesive and user-centered product interface.

## When to Use This Skill

- User asks to start stage 06 (ux)
- User wants to create wireframes or design system
- User asks about UI design, accessibility, or responsive design

## Your Roles in This Skill

See `dev-swarm/docs/general-dev-stage-rule.md` for role selection guidance.

## Role Communication

See `dev-swarm/docs/general-dev-stage-rule.md` for the required role announcement format.

## Pre-Stage Check

Before starting, verify previous stages:

1. Check if `00-init-ideas/` through `05-prd/` folders have content (not just `.gitkeep`)
2. If any previous stage is empty and has no `SKIP.md`:
   - Ask user: "Stage {XX} is not complete. Would you like to skip it or start from that stage first?"

## Instructions

### Step 1: Context Review

Read all files to understand the project:

- `ideas.md`
- `00-init-ideas/*.md` through `05-prd/*.md` - All markdown files

### Step 2: Create Stage Proposal

**General Rules:** See `dev-swarm/docs/general-dev-stage-rule.md` → "Create Stage Proposal Rules" section.

If this stage is skipped (has SKIP.md), execute the next non-skipped stage's agent skill. Otherwise, create the file `06-ux/README.md` with the following content:

#### 2.1 Stage Goal

Brief the goal in 2-3 paragraphs:
- What this stage aims to achieve
- Why UX design is critical for product success and user adoption
- How this builds upon previous stages (personas, MVP scope, PRD)
- What deliverables will be produced

#### 2.2 File Selection

Select files from these options based on project needs:

**Design System:**
- `design-system-guide.md` - Color palette, typography, spacing, and button styles
- `design-ui-preview.html` - Sample HTML/CSS/JS page demonstrating the design system

**Wireframes & Layouts:**
- `wireframe_descriptions.md` - Textual descriptions of UI layout for each key screen

**User Flows & Navigation:**
- `user-flows/` - User navigation flow diagrams

**Responsive & Accessibility:**
- `responsive-design.md` - Guidelines for how UI adapts across screen sizes
- `accessibility.md` - Accessibility requirements following WCAG guidelines

**UI Mockups (for GUI projects):**
- `design-ui-mockup/README.md` - Mockup proposal listing all pages/screens to be created (include in this approval step; mockup files created after design system approval). Required for any web, mobile, or desktop app with a graphic user interface when HTML mockups can express workflow.

For each selected file, provide:
- Short description
- Why it's essential for this project
- Key information it should include

**Note:** If `design-ui-mockup/` is selected, include `design-ui-mockup/README.md` (mockup proposal) in this stage proposal for approval together with other files. The actual mockup HTML/CSS/JS files will be created in Step 4 after design system files are approved.

#### 2.3 Request User Approval

Ask user: "Please check the Stage Proposal in `06-ux/README.md`. Update it directly or tell me how to update it."

### Step 3: Execute Stage Plan

Once user approves `06-ux/README.md`:

#### 3.1 Create All Planned Files

Create each file listed in the approved README:

- **For `.md` files:** Write comprehensive content based on personas, MVP requirements, and PRD
- **For diagram folders:** Follow `dev-swarm/docs/mermaid-diagram-guide.md` to create related diagrams files
- **For `.html` files:** Create functional preview pages demonstrating the design system with css/js as needed
- **For `design-ui-mockup/README.md`:** Create the mockup proposal (see format below)

**Mockup Proposal Format (for `design-ui-mockup/README.md`):**

**Purpose Statement:**
- These mockups are NOT the final design implementation
- They serve as visual references for user review of the final layout, navigation flow, and overall user experience before actual development begins

**Page/Screen List:**
Based on wireframes and user flows, list all pages/screens to be created:
- Page name
- Brief description
- Key components/sections on this page
- Navigation links to other pages

**Shared Assets:**
- `styles.css` - Design system styles (colors, typography, spacing, buttons)
- `navigation.js` - Inter-page navigation simulation

**Proposed Structure:**
```
design-ui-mockup/
├── README.md           # This proposal (will become review instructions after approval)
├── index.html          # Entry point / landing page
├── home.html           # Home/dashboard
├── login.html          # Authentication screens
├── [feature].html      # Feature-specific pages
├── styles.css          # Shared design system styles
└── navigation.js       # Inter-page navigation
```

**Quality Guidelines:**
- Base design decisions on user personas and their needs
- Align UX with MVP features defined in stage 03
- Ensure all user flows support functional requirements from stage 05
- Accessibility must meet WCAG 2.1 AA standards at minimum

#### 3.2 Request User Approval for Files

After creating all files (including `design-ui-mockup/README.md` if applicable):
- Provide a summary of what was created
- Highlight key design decisions and rationale
- Ask: "Please review the UX design files. You can update or delete files, or let me know how to modify them."

### Step 4: Create UI Mockups (For GUI Projects)

**Trigger Condition:** Execute this step if:
- The project has a GUI component (web app, mobile app, desktop app)
- `design-ui-mockup/README.md` was created and approved by user in Step 3

UI mockups are required for GUI projects where HTML pages can represent the workflow, including this project.

#### 4.1 Create Mockup Files

Create all mockup files based on the approved `design-ui-mockup/README.md`:

**For each page/screen listed in the approved proposal, create:**
- **Individual HTML files:** One file per page/screen (e.g., `home.html`, `login.html`, `dashboard.html`, `settings.html`)
- **Shared CSS:** `styles.css` - Apply design system (colors, typography, spacing, buttons)
- **Navigation JS:** `navigation.js` - Enable clicking between pages to simulate user flow

**Content Guidelines:**
- Use **fake/placeholder data** for all text content (lorem ipsum, sample names, mock statistics)
- Use **placeholder images** (solid color boxes with dimensions, or placeholder.com URLs)
- Use **placeholder videos** (colored rectangles with play button overlay)
- Include **all interactive states** (hover, active, disabled) where applicable
- Show **responsive breakpoints** if responsive design is required

#### 4.2 Update Mockup README

After creating all mockup files, update `06-ux/design-ui-mockup/README.md` to include:
- How to open and navigate the mockups (open index.html in browser)
- Complete list of all pages/screens created
- Navigation flow instructions (which pages link to which)
- Notes on placeholder content

#### 4.3 Request User Approval for Mockups

After creating all mockups:
- Provide a summary of pages/screens created
- Explain how to navigate through the mockup flow
- Ask: "Please review the UI mockups by opening `design-ui-mockup/index.html` in your browser. These mockups show the final layout and navigation flow. Let me know if any changes are needed before we proceed."

### Step 5: Finalize Stage

Once user approves all files (and mockups if applicable):

#### 5.1 Documentation Finalization
- Sync `06-ux/README.md` to remove any deleted files
- Ensure all files are complete and well-formatted
- Check that all diagrams render correctly
- Validate HTML preview and mockups display correctly

#### 5.2 Prepare for Next Stage
- Summarize key design decisions for reference in architecture stage
- Note any technical constraints discovered during UX design
- Reference mockups as the visual baseline for implementation

#### 5.3 Announce Completion

Inform user:
- "Stage 06 (UX Design) is complete"
- Summary of deliverables created
- Key design decisions made
- "Ready to proceed to Stage 07 (Architecture) when you are"

## Stage Completion Rules

See `dev-swarm/docs/general-dev-stage-rule.md` for stage completion, commit, and skip rules.

## Key Principles

- Base design on user personas and needs
- Ensure accessibility compliance
- Keep design consistent across all screens
- Support smooth transition to architecture design
