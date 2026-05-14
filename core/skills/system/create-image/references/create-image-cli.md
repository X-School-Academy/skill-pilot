# create-image CLI Usage

Use this CLI when Codex image generation is unavailable or fails. It sends the request to the running Skill Pilot engine through the local socket, so the CLI process does not read `config/.env`.

## Command

```bash
core/bin/create-image --ratio square --prompt "A clean app icon for an AI skill builder, layered cards and a small spark, crisp vector-like 3D render, white background"
```

## Arguments

- `--ratio`: one of `square`, `landscape`, or `portrait`.
- `--prompt`: the full image prompt.

## Ratio Guidance

- `square`: app icons, avatars, logos, stickers, thumbnails that will be cropped, product badges.
- `landscape`: YouTube covers, blog headers, presentation hero images, banners, website hero imagery.
- `portrait`: posters, mobile story assets, vertical covers, character portraits, phone wallpapers.

## Output

On success, the CLI prints the generated image file path to stdout.

On failure, it prints an error to stderr and exits non-zero.

## Examples

```bash
core/bin/create-image --ratio landscape --prompt "YouTube cover for a tutorial about building AI agent skills, modern workstation, clear focal point, bold empty space on the left for title text, high contrast, professional tech style"
```

```bash
core/bin/create-image --ratio portrait --prompt "Vertical poster for a beginner AI workshop, friendly teacher at a desk with diagrams, clean editorial illustration, warm lighting, readable empty top area"
```
