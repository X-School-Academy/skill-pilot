# Showcase Prompt Writing

The `prompt` field is the user's starter request to the AI agent. Write it like a user would ask for the outcome, not like internal instructions for how an agent should perform the work.

## Requirements

- Keep the prompt concise, outcome-focused, and runnable.
- Include user-facing details that shape the desired result: topic, audience, tone, constraints, review checkpoints, output location, and requested deliverables.
- Reference provided files with `@path/to/file` when the user must supply or use a concrete file.
- When a referenced `requirements.md`, `update.md`, or `issues.md` already defines the detailed requirements, do not repeat those details in `prompt`. State the desired outcome, point to the file, and include only high-level workflow requests such as "show me the plan first", "run tests", or "document the result".
- Use the showcase `directory` path for every file reference. Do not reference the packaging source directory `workspace/showcases/{showcase_slug_id}/` from the user-facing prompt.
- Include the destination directory context whenever the prompt depends on a file. Example: `Use @workspace/tasks/cloud-setup-aws-credentials/requirements.md`.
- Ask for missing user inputs only when they are part of the natural task request.

## Do Not Include

- Role labels such as "You are my..." or "Role:".
- Step-by-step implementation instructions such as "Steps:" or numbered tool operations.
- Skill names, tool names, model names, shell commands, package managers, framework choices, or internal routing details.
- Detailed requirement lists that are already present in a referenced file.
- Low-level technical details that belong to the selected agent skill, MCP tool, workflow, or implementation plan.

## Put Metadata Elsewhere

- Use `skills`, `tools`, `workflow`, and `extensions` for agent routing.
- Use `terms` for technology concepts users can explore afterwards.
- Use `goals` for learning outcomes.
- Use `requirements.md`, `update.md`, or `issues.md` for detailed product, engineering, or reverse-engineering requirements.

## Examples

Good:

```yaml
directory: workspace/tasks/story-video-for-kids
prompt: |-
  Create a kids audio book video about the story of "The Tortoise and the Hare".

  Make it suitable for young children, with warm narration, colorful storybook
  scenes, gentle pacing, and a clear moral about patience and steady effort.
  Show me the planned scenes before creating the final video.
```

Good with a copied reference file:

```yaml
directory: workspace/tasks/cloud-setup-aws-credentials
prompt: |-
  Set up my AWS credentials safely.

  Use @workspace/tasks/cloud-setup-aws-credentials/requirements.md as the task brief.
  Show me the plan before making changes, then guide me through setup and validation.
```

Avoid:

```yaml
prompt: |-
  Role: You are my video producer.

  Skills to use:
  - create-slide-show-video

  Steps:
  1. Generate images with a specific image model.
  2. Use ffmpeg to assemble the final MP4.
```

Avoid repeating a referenced brief:

```yaml
prompt: |-
  Build the S3 manager described in @workspace/vibe-coding/aws-s3-manager/requirements.md.

  It must support drag-and-drop uploads, CLI uploads, CloudFront previews,
  image previews, video previews, website deletes, CLI deletes, SQLite metadata,
  sync buttons, separate website and CLI operation, and `.env` configuration.
```

Better:

```yaml
prompt: |-
  Build a local AWS S3 and CloudFront file manager.

  Use @workspace/vibe-coding/aws-s3-manager/requirements.md as the product brief.
  Show me the implementation plan before coding, then build, run, test, and
  document the result.
```

## Links

Use `links` for knowledge the learner may explore after running the showcase. Each entry should represent one underlying term or concept from `terms`, not the whole showcase.

- Use `url` for existing external references, especially official documentation or stable project docs.
- Use `prompt` when you want Skill Pilot to generate an extra tutorial video or online interactive course for that topic.
- Scope each `prompt` to one reusable topic, such as `Environment variables`, `SQLite`, or `Prompt injection`.
- Do not use `links[].prompt` to repeat the showcase tutorial. The showcase-specific tutorial belongs in `tutorial_prompt`.
- Usually choose either `url` or `prompt` for a link. If a `url` is present, omit `prompt` unless the generated lesson should explicitly complement that external reference.

External reference link:

```yaml
links:
  - name: Amazon S3
    url: https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html
```

Generated learning prompt:

```yaml
links:
  - name: Environment variables
    prompt: |-
      Create a practical beginner lesson about using environment variables and
      `.env` files in local apps. Explain what belongs in environment variables,
      why secrets should not be committed, how applications load them, and how
      to document required values safely.
```
