# Output Package

Use this reference to decide the output structure for Architecture Explorer results.

## Full Output Package

When the input is a remote repository and the user does not provide a checkout location, use this default temporary source directory:

```text
.skillpilot/temp/{project}/
```

When the user asks to save architecture/research output and does not provide a documentation location, use this default documentation directory:

```text
workspace/research/{project}/
```

If the user provides a requirement, task, or instruction file, use that file's parent folder as the documentation output directory by default. This overrides `workspace/research/{project}/`.

Derive `{project}` from the input repository or folder name:

- GitHub `owner/repo` -> `repo`
- Local folder `/path/to/my-app` -> `my-app`
- Zip file `my-app.zip` -> `my-app`

Normalize the project name to a short filesystem-safe slug using lowercase letters, numbers, dots, underscores, and hyphens. If the user provides an explicit output path, use that instead.

Create a full output package using this structure:

```text
workspace/research/{project}/
  README.md
  00-executive-summary.md
  01-language-independent-architecture.md
  02-current-tech-stack.md
  03-module-map.md
  04-core-workflows.md
  05-data-model.md
  06-interface-and-boundary-map.md
  07-runtime-and-deployment-view.md
  08-design-and-performance-review.md
  09-remake-guide.md
  10-learning-guide.md
  index.html
  diagrams/
    system-context.mmd
    component-map.mmd
    workflow-main.mmd
    sequence-main-flow.mmd
    data-flow.mmd
    deployment-view.mmd
  evidence/
    architecture-claims.json
    uncertain-points.md
    file-evidence-map.md
```

## README Requirements

The documentation package `README.md` must include:

- Project name.
- Project Git URL when available, or the source location if the input was local or uploaded.
- Temporary source checkout location, normally `.skillpilot/temp/{project}/`.
- Documentation output location, normally `workspace/research/{project}/`.
- A short index of the generated Markdown files.
- A link or instruction to open `index.html` for Mermaid diagrams.

## HTML Mermaid Viewer

For saved packages, always create `index.html` at the documentation output root.

The viewer should:

- Render the Mermaid diagrams from the package in the browser.
- Provide simple navigation between diagrams.
- Work as a static file when opened directly when practical.
- Prefer embedding diagram source strings in the HTML so local `file://` browsing does not fail because of fetch/CORS restrictions.
- Use a Mermaid browser runtime, such as the Mermaid ESM bundle from a CDN, unless the user requests an offline-only artifact.
- Keep the page focused on diagrams and links to the Markdown docs; do not turn it into a marketing page.
- Include the same diagram set listed under `diagrams/` unless a mode-specific output intentionally produces fewer diagrams.

## Quick Output

If the user only wants a quick answer, produce a shorter version with:

```text
1. Summary
2. Component map
3. Main workflow
4. Mermaid diagram
5. Key design/performance issues
6. Remake guidance
```

If Quick Mode is saved to files, still use `workspace/research/{project}/` by default and include `README.md`, at least one Mermaid `.mmd` file, and `index.html`.
