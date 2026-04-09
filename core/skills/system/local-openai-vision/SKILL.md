---
name: local-openai-vision
description: Analyze a local image with the local OpenAI-compatible vision endpoint to describe screenshot, video scenes, answer image questions, extract visible text, or perform OCR-style image-to-text tasks.
---

# AI Builder - Local OpenAI Vision

Use this skill when an image should be analyzed through the local OpenAI-compatible vision endpoint instead of a remote hosted model.

## When to Use This Skill

- Describe a local image in natural language
- Read visible text from screenshots, photos, or scanned documents
- Answer targeted questions about image contents
- Perform OCR-style extraction from UI screenshots, posters, receipts, slides, or forms

## Your Roles in This Skill

- **Project Manager**: Confirm the image task and choose the most direct prompt style for the requested output
- **AI Engineer**: Route the request through the local vision CLI and shape prompts for description or OCR accuracy
- **Technical Writer**: Return the extracted text or description in a clear format that matches the user's request

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role, and Role-XYZ if have more roles}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order:

### Step 1: Confirm the local image input

- Prefer a local file path provided by the user
- If the user gave a relative path, resolve it from the repo root before running the command
- If the file does not exist, stop and report the missing path clearly

### Step 2: Choose the right prompt mode

- For a general description request, ask for a concise or detailed scene description
- For OCR or image-to-text, ask to transcribe all visible text and preserve line breaks when useful
- For targeted questions, include the specific question directly in the prompt
- If the user wants strict extraction, instruct the model to avoid adding commentary beyond the visible text

### Step 3: Run the local vision command

- Use `core/bin/local-openai-infer --type image`
- Pass the prompt with `--prompt`
- Pass the image path with `--file_path`
- If model or endpoint specifics matter, refer to `references/local-openai-infer.md`

### Step 4: Return the result clearly

- For OCR, present the extracted text directly and note uncertainty only when the output is ambiguous
- For image description, summarize the important visible details without extra filler
- If the result appears incomplete or low confidence, suggest a tighter follow-up OCR prompt or a cropped image

## Expected Output

- A plain-text image description, answer, or OCR extraction based on the user's request
- Clear note of uncertainty only when the visible text or image content is ambiguous

## Key Principles

- Prefer the local endpoint over remote vision APIs for this skill
- Keep prompts explicit about whether the goal is description, Q&A, or OCR
- Preserve visible text faithfully for OCR-style tasks
