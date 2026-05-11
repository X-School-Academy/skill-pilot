---
name: create-image
description: Create AI-generated image files from prompts for product, marketing, education, social, and UI asset work. Use when the user asks to generate an image, icon, thumbnail, cover, illustration, mockup, avatar, poster, or other raster visual and wants a local file path output.
---

# AI Builder - Create Image

Create local AI-generated image files from clear visual prompts, choosing the strongest available route and falling back when needed.

## When to Use This Skill

- The user asks to create or generate a new image file.
- The requested output is a raster visual such as an icon, YouTube cover, thumbnail, poster, product mockup, scene illustration, avatar, or social graphic.
- A local file path is needed as the result.

## Your Roles in This Skill

- **AI Engineer**: Convert the user's intent into an effective image generation prompt and choose the best generation path.
- **UX Designer**: Shape the composition, ratio, style, and visual constraints so the image is useful for its target context.
- **Technical Writer**: Report the generated file path and any important usage notes clearly.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Clarify the Output

Identify the image type, intended use, required ratio, important subject matter, style, text constraints, brand constraints, and final file-path expectations. If the user did not specify a ratio, choose the most appropriate one for the use case.

### Step 2: Build the Prompt

Write a concrete visual prompt with composition, subject, medium, lighting, color direction, texture, camera or layout notes, and constraints. For prompt patterns by asset type, refer to `references/image-prompt-guide.md`.

### Step 3: Generate with Codex When Available

If Codex is available, use Codex execution with a prompt that asks it to use the `imagegen` skill and return the local generated file path. For invocation guidance, refer to `references/codex-imagegen.md`.

### Step 4: Fall Back to the CLI

If Codex image generation is unavailable, fails, or does not produce a usable file path, use the local CLI fallback. For CLI usage, refer to `references/create-image-cli.md`.

### Step 5: Verify and Report

Check that the reported path is present and points to an image file when possible. Return the local file path as the primary result, with a short note only if a fallback was needed or verification could not be completed.

## Expected Output

A local image file path, plus brief context when useful.
