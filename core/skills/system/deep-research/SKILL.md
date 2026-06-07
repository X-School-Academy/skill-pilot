---
name: deep-research
description: Perform deep research from a research requirement or instruction file and produce research outputs in the same folder, including Markdown plus an index.html visual report with Mermaid diagrams when useful.
---

# AI Builder - Deep Research

Perform a structured research pass from a research requirement file.

## When to Use This Skill

- The user wants a deep research result from `workspace/research/{topic}/requirements.md`
- The user provides any requirement, task, or instruction file and wants the result written beside it
- The work requires gathering, organizing, and synthesizing research findings
- The output should be written back into the topic workspace

## Your Roles in This Skill

- **Research Analyst**: Gather and synthesize relevant findings
- **Technical Writer**: Turn findings into a clear output document

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

### Step 1: Read the Requirement

Read the referenced research `requirements.md` carefully and identify the scope, research questions, and expected deliverable.

If the user provides a requirement, task, or instruction file path, use that file's parent folder as the output folder unless the user explicitly provides another output path.

### Step 2: Perform the Research

Gather and synthesize the most relevant information for the requested topic.

### Step 3: Write the Result

Save the result inside the same folder as the instruction file when one exists. Markdown is the default source format.

When the result benefits from visual explanation, also create:

```text
index.html
```

The HTML report should be a polished visual report, not just raw Markdown. Use Mermaid diagrams, tables, sections, and navigation when useful. Put any Mermaid source files, images, or supporting assets in the same folder or a child folder so the report works as a static page rooted at that folder. If Mermaid diagrams are included, also save their `.mmd` source files where practical.

If the task benefits from a document-style deliverable, a PDF output is also acceptable, but it should not replace the Markdown/HTML outputs unless the user specifically asks for only PDF.

### Step 4: Summarize the Output

Tell the user what was created and where it was saved.
