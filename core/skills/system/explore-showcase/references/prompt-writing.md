# Showcase Prompt Writing

The `prompt` field is the user's starter request to the AI agent. Write it like a user would ask for the outcome, not like internal instructions for how an agent should perform the work.

## Requirements

- Keep the prompt concise, outcome-focused, and runnable.
- Include user-facing details that shape the desired result: topic, audience, tone, constraints, review checkpoints, output location, and requested deliverables.
- Reference provided files with `@path/to/file` when the user must supply or use a concrete file.
- Ask for missing user inputs only when they are part of the natural task request.

## Do Not Include

- Role labels such as "You are my..." or "Role:".
- Step-by-step implementation instructions such as "Steps:" or numbered tool operations.
- Skill names, tool names, model names, shell commands, package managers, framework choices, or internal routing details.
- Low-level technical details that belong to the selected agent skill, MCP tool, workflow, or implementation plan.

## Put Metadata Elsewhere

- Use `skills`, `tools`, `workflow`, and `extensions` for agent routing.
- Use `terms` for technology concepts users can explore afterwards.
- Use `goals` for learning outcomes.
- Use `requirements.md`, `update.md`, or `issues.md` for detailed product, engineering, or reverse-engineering requirements.

## Examples

Good:

```yaml
prompt: |
  Create a kids audio book video about the story of "The Tortoise and the Hare".

  Make it suitable for young children, with warm narration, colorful storybook
  scenes, gentle pacing, and a clear moral about patience and steady effort.
  Show me the planned scenes before creating the final video.
```

Avoid:

```yaml
prompt: |
  Role: You are my video producer.

  Skills to use:
  - create-slide-show-video

  Steps:
  1. Generate images with a specific image model.
  2. Use ffmpeg to assemble the final MP4.
```
