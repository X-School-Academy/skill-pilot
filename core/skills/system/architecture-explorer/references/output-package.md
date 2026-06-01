# Output Package

Use this reference to decide the output structure for Architecture Explorer results.

## Full Output Package

Create an output package using this structure:

```text
architecture-explorer-output/
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
