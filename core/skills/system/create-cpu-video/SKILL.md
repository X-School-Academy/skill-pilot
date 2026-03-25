---
name: create-cpu-video
description: Create a CPU video from a written requirement. Use when the user wants a generated video with multiple scenes, image and audio support, educational or presentation-style structure, or HTML-style animation and visual storytelling.
---

# AI Builder - Create CPU Video

This skill creates a CPU video from a requirement. The request can describe multi-scene output, image and audio support, educational or presentation-style structure, and HTML or animation-oriented visual goals.

## When to Use This Skill

- The user asks to create a CPU video.
- The user wants to generate a video from a written requirement.
- The user describes a multi-scene educational or presentation-style video.
- The user wants image, audio, or animation-oriented output expressed as a requirement.
- The user provides a requirement plus optional `target_duration` or `resolution`.

## Your Roles in This Skill

- **Project Manager**: Confirm the required inputs and keep the invocation focused on the user's requested output.
- **Backend Developer**: Build the JSON payload correctly and run `core/bin/api-invoke create_cpu_video`.
- **Technical Writer**: Return the result clearly, including the generated video path or the concrete failure reason.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role} [and {Role}, ...], I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Gather Inputs

Read the user's request and extract:

- `requirement`: required
- `target_duration`: optional, default `60`
- `resolution`: optional, default `1080x1920`

If `requirement` is missing, ask the user for it before invoking the API.

### Step 2: Build the Payload

Create a JSON object with:

- `requirement`
- `target_duration`
- `resolution`

If the user omits optional fields, use the defaults above.

For the exact command contract, refer to `references/api-invoke.md`.

### Step 3: Invoke the API

Run `core/bin/api-invoke create_cpu_video '<json-payload>'` from the repo root.

- Pass a valid JSON object string.
- Treat engine or workflow failures as task failures and surface the returned error.

### Step 4: Return the Result

If the command succeeds, report the resulting `video_file_path`.

If the command fails, report the exact API or command error and state which payload values were used.

## Expected Output

- Success: the generated video file path.
- Failure: a concise error that includes the attempted payload values.

## Key Principles

- Keep the payload minimal and valid JSON.
- Use the documented defaults unless the user gives explicit overrides.
- Prefer surfacing the engine's actual error instead of rewriting it.
