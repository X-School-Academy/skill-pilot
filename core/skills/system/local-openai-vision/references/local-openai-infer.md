# Local OpenAI Infer Reference

Use the local CLI wrapper directly from the repo root:

```bash
core/bin/local-openai-infer --type image --prompt "Describe this image." --file_path /absolute/path/to/image.png
```

## Prompt Patterns

- General description:
  `Describe this image clearly and briefly.`
- Detailed description:
  `Describe this image in detail, including people, objects, setting, colors, and notable context.`
- OCR / image to text:
  `Extract all visible text from this image. Preserve line breaks. Do not add commentary.`
- UI screenshot OCR:
  `Read all visible text in this screenshot. Group related labels with their nearby values. Do not invent missing text.`
- Targeted question:
  `Answer this question about the image: {question}`

## Optional Overrides

- Set `LOCAL_OPENAI_BASE_URL` to point at the local OpenAI-compatible endpoint
- Set `LOCAL_OPENAI_INFER_MODEL` if the local server expects a specific model name
- Set `LOCAL_OPENAI_INFER_API_KEY` only if the local server requires one

## Notes

- The CLI prints only the response text
- If OCR quality is poor, retry with a narrower prompt or a cropped image focusing on the text region
