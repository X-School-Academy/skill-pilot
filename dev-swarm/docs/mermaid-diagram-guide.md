# Mermaid Diagram Guide

This guide defines how to create Mermaid diagrams across stages.
Use it as the standard for diagram structure and rendering.

## Purpose

- Keep diagrams lightweight but consistent across stages.
- Avoid over-engineering by matching effort to project scale.
- Ensure diagram outputs are human-reviewable and AI-readable.

## Where Diagrams Live

Each stage folder may include one `diagram-name/` or more directories:

```
diagram-name/
  README.md
  index.html
  images/
    diagram1.svg
    diagram2.svg
    ...
```

Notes:

- AI agents read only `.md` files.
- Humans review `.html` and `.svg` outputs.

## Creation Rules

- All Mermaid source lives in markdown files in `diagram-name/`.
- Use agent skill `dev-swarm-mermaid` to render:
  - `images/*.svg` for the html file for review
  - `.html` for human-in-the-loop feedback
- If Mermaid code fails to render, fix the code before re-running.
