---
name: pdf
description: Use when tasks involve reading, creating, or reviewing PDF files where rendering and layout matter; prefer visual checks by rendering pages and use Python tools such as reportlab, pdfplumber, and pypdf for generation and extraction.
---


# AI Builder - PDF Skill

## When to Use This Skill

- Read or review PDF content where layout and visuals matter.
- Create PDFs programmatically with reliable formatting.
- Validate final rendering before delivery.

## Your Roles in This Skill

- **Backend Developer (Engineer)**: Generate, parse, and transform PDF files using reliable libraries
- **QA Engineer**: Validate rendered output quality and catch layout regressions
- **Technical Writer**: Ensure document structure, readability, and polished formatting

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Confirm PDF task goal

Identify whether the user needs:

1. PDF generation
2. PDF text extraction
3. PDF visual/layout review
4. A combination of the above

### Step 2: Ensure required tools are available

For Python package installs and Python/package execution in this repo, use the `python-package-runtime` system skill.

Python packages:
```
reportlab pdfplumber pypdf
```
System tools (for rendering):
```
# macOS (Homebrew)
brew install poppler

# Ubuntu/Debian
sudo apt-get install -y poppler-utils
```

If installation isn't possible in this environment, report the missing dependency and the failed command.

### Step 3: Execute PDF workflow

1. Prefer visual review: render PDF pages to PNGs and inspect them.
2. Use `reportlab` to generate PDFs when creating new documents.
3. Use `pdfplumber` or `pypdf` for text extraction and structural checks.
4. Re-render pages after meaningful updates and verify alignment, spacing, and legibility.

When implementing helpers for this workflow, follow the `python-package-runtime` skill conventions for package install, Python script execution, and package CLI execution.

### Step 4: Apply temp and output conventions

- Use `tmp/pdfs/` for intermediate files; delete when done.
- Write final artifacts under `output/pdf/` when working in this repo.
- Keep filenames stable and descriptive.

### Step 5: Run final visual and quality checks

Use the quality expectations and final checks below before delivery.

## Environment
No required environment variables.

## Rendering command
```
pdftoppm -png $INPUT_PDF $OUTPUT_PREFIX
```

## Quality expectations
- Maintain polished visual design: consistent typography, spacing, margins, and section hierarchy.
- Avoid rendering issues: clipped text, overlapping elements, broken tables, black squares, or unreadable glyphs.
- Charts, tables, and images must be sharp, aligned, and clearly labeled.
- Use ASCII hyphens only. Avoid U+2011 (non-breaking hyphen) and other Unicode dashes.
- Citations and references must be human-readable; never leave tool tokens or placeholder strings.

## Final checks
- Do not deliver until the latest PNG inspection shows zero visual or formatting defects.
- Confirm headers/footers, page numbering, and section transitions look polished.
- Keep intermediate files organized or remove them after final approval.
