---
name: merge-research-results
description: Merge multiple research outputs from different agents into one final research result. Use when a workflow gathers parallel findings from multiple agents and needs a final consolidated output.
---

# AI Builder - Merge Research Results

Combine multiple research outputs from different agents into one coherent final result.

## When to Use This Skill

- A workflow has parallel research outputs from multiple agents
- The user wants one final synthesized result
- The final step should consolidate overlap, gaps, and contradictions

## Your Roles in This Skill

- **Research Analyst**: Compare findings across sources and resolve conflicts
- **Technical Writer**: Produce a clear final result

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

### Step 1: Read All Upstream Research Outputs

Read the research outputs produced by the prior agents in the workflow.

### Step 2: Compare and Synthesize

Identify agreement, disagreement, missing areas, and the strongest useful insights.

### Step 3: Produce the Final Result

Write one merged final result that is coherent, non-duplicative, and useful to the user.

### Step 4: Preserve Important Differences

If the agent outputs disagree in a meaningful way, state that clearly instead of hiding the conflict.

## Expected Output

Output result as plain text. If the user asked to save it to a file, write it there.

The plain-text output should make clear that it is the merged final research result and should briefly indicate which upstream agent outputs were consolidated.
