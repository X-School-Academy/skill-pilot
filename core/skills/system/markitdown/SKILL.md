---
name: markitdown
description: "Convert files or URLs to Markdown. Supports PDF, DOCX, PPTX, XLS, XLSX, HTML, CSV, JSON, XML, Images, and YouTube URLs."
---

# Markitdown

Convert a file or URL to Markdown using the `markitdown` CLI.

## When to Use This Skill

- The user wants to convert a document (PDF, DOCX, PPTX, XLS, XLSX, etc.) to Markdown
- The user wants to extract text content from a web page URL as Markdown
- The user wants to transcribe a YouTube video to Markdown
- The user needs to read or process a non-text file as Markdown for further use

## Supported Formats

- **PDF** - text extraction via pdfminer/pdfplumber
- **DOCX** - Word documents via mammoth
- **PPTX** - PowerPoint presentations
- **XLS/XLSX** - Excel spreadsheets
- **HTML** - web pages (built-in)
- **CSV, JSON, XML** - structured data (built-in)
- **YouTube URLs** - video transcription via youtube-transcript-api
- **Images** (PNG, JPG, WEBP, GIF, etc.) - via AI agent vision (see below)

## Usage

Run the CLI wrapper:

```bash
# Output to stdout
core/bin/markitdown <input>

# Output to a file
core/bin/markitdown <input> -o <output.md>
```

**Do not use any Python helper code to invoke the `core/bin/markitdown` command. Run as shell command with arguments directly.**

### Examples

```bash
# Convert a PDF to markdown
core/bin/markitdown report.pdf -o report.md

# Convert a DOCX file
core/bin/markitdown document.docx -o document.md

# Convert a spreadsheet
core/bin/markitdown data.xlsx -o data.md

# Convert a web page
core/bin/markitdown https://example.com/article.html -o article.md

# Transcribe a YouTube video
core/bin/markitdown "https://www.youtube.com/watch?v=VIDEO_ID" -o transcript.md

# Output to stdout for inline use
core/bin/markitdown document.pdf
```

## Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `input`  | Yes      | File path or URL to convert |
| `-o`     | No       | Output file path (defaults to stdout) |

## Image Handling

Do **not** use the CLI for images. Instead, use the AI agent's built-in vision capability:

1. Read the image file directly (the agent can view images natively).
2. Describe the image content in Markdown format, including:
   - Text and labels visible in the image (OCR)
   - Tables or structured data shown in the image
   - Diagrams, charts, or visual layouts
   - General description of the scene or content
3. Save the resulting Markdown to the output file if `-o` was specified, or return it directly.

## Notes

- For large files, the conversion may take a moment depending on file size and format.
- When no `-o` flag is provided, the Markdown output is printed to stdout.
- Audio transcription is NOT installed. Only the extras `docx,pdf,pptx,xls,xlsx,youtube-transcription` are available.
