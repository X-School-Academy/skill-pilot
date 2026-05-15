---
name: create-image-audio
description: Create AI-generated image or text-to-speech audio files and return local file paths. Use when the user asks to generate raster visuals such as icons, thumbnails, covers, mockups, or posters, or asks to turn plain text into audio formats such as mp3 or wav.
---

# AI Builder - Create Image Audio

Create local AI-generated image files from clear visual prompts, or text-to-speech audio files from plain text, choosing the strongest available route and falling back when needed.

## When to Use This Skill

- The user asks to create or generate a new image file.
- The requested output is a raster visual such as an icon, YouTube cover, thumbnail, poster, product mockup, scene illustration, avatar, or social graphic.
- The user asks to create narration, speech, voiceover, or other text-to-speech audio from plain text.
- The requested audio output format is specified or can be inferred, such as `mp3` or `wav`.
- A local file path is needed as the result.

## Your Roles in This Skill

- **AI Engineer**: Convert the user's intent into an effective image generation prompt and choose the best generation path.
- **UX Designer**: Shape the composition, ratio, style, and visual constraints so the image is useful for its target context.
- **Audio Producer**: Prepare concise, speakable text and choose the requested audio format.
- **Technical Writer**: Report the generated file path and any important usage notes clearly.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Clarify the Output Type

Decide whether the user needs an image or text-to-speech audio.

For images, identify the image type, intended use, required ratio, important subject matter, style, text constraints, brand constraints, and final file-path expectations. If the user did not specify a ratio, choose the most appropriate one for the use case.

For audio, identify the exact text to speak, requested output format, and final file-path expectations. If the user did not specify a format, use `mp3`.

### Step 2: Prepare the Request

For images, write a concrete visual prompt with composition, subject, medium, lighting, color direction, texture, camera or layout notes, and constraints. For prompt patterns by asset type, refer to `references/image-prompt-guide.md`.

For audio, keep the text plain and speakable. Do not add stage directions or commentary unless the user explicitly asked for them.

### Step 3: Generate the File

For images, use Codex image generation first when available. For invocation guidance, refer to `references/codex-imagegen.md`.

For audio, use the local CLI. For CLI usage, refer to `references/create-audio-cli.md`.

### Step 4: Fall Back When Needed

If Codex image generation is unavailable, fails, or does not produce a usable file path, use the image CLI fallback. For CLI usage, refer to `references/create-image-cli.md`.

### Step 5: Verify and Report

Check that the reported path is present and points to the expected file type when possible. Return the local file path as the primary result, with a short note only if a fallback was needed or verification could not be completed.

## Expected Output

A local image or audio file path, plus brief context when useful.
