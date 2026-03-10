---
name: deep-research
description: Perform deep research from a research requirement file and produce research outputs such as markdown or PDF files in the topic workspace. Use when a user wants a substantial research pass from workspace/research/{topic}/requirements.md.
---

# AI Builder - Deep Research

Perform a structured research pass from a research requirement file.

## When to Use This Skill

- The user wants a deep research result from `workspace/research/{topic}/requirements.md`
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

### Step 2: Perform the Research

Gather and synthesize the most relevant information for the requested topic.

### Step 3: Write the Result

Save the result inside the same topic workspace. Markdown is the default. If the task benefits from a document-style deliverable, a PDF output is also acceptable.

### Step 4: Summarize the Output

Tell the user what was created and where it was saved.
