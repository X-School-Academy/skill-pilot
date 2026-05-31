# Codex Imagegen Usage

Use Codex first when it is available because it can call the built-in `imagegen` skill directly.

## When to Use

- Use this path before the CLI fallback.
- Prefer it for rich creative prompts where the imagegen skill can generate the raster image directly.
- Use the ratio requested by the user, or infer it from the asset type.

## Command Pattern

```bash
codex exec "Use the imagegen skill to create a <ratio> image from this prompt: <prompt>. Save the generated image as a local file and print only the absolute file path."
```

Use one of these ratio words:

- `square`
- `landscape`
- `portrait`

## Prompt Requirements

Ask Codex to:

- Use the `imagegen` skill.
- Create a raster image, not an SVG or HTML mockup.
- Save the image locally.
- Print only the absolute file path on success.
- Avoid extra commentary when a path is produced.

## Failure Conditions

Treat the Codex path as failed if:

- The `codex` command is not found.
- The command exits non-zero.
- The output does not include a plausible local file path.
- The path does not exist after generation.
- The output is a URL only and the user specifically needs a local file.

When any of these happen, use `core/bin/create-image`.
