# GPU Workflow Files

This directory contains ComfyUI workflow JSON files for different task types.

## Workflow Naming Convention

Workflow files must be named: `workflow_{task_type}.json`

Example:
- `workflow_image-to-video.json`
- `workflow_image-to-talk-video.json`
- `workflow_video-continuation.json`

## Placeholder System

Workflows can use placeholders that will be replaced with actual values at runtime:

### Text Placeholders
- `{{ratio}}` - Image ratio (for image tasks)
- `{{frame_index}}` - Frame index (for video continuations)

### File Placeholders
- `{{source_image}}` - Downloaded source image path
- `{{source_video}}` - Downloaded source video path
- `{{ref_audio}}` - Downloaded reference audio path
- `{{ref_audio_1}}` - First reference audio (for dialog/questions)
- `{{ref_audio_2}}` - Second reference audio (for dialog)

### Complex Data
- `{{dialog}}` - JSON array of dialog entries
- `{{questions}}` - JSON array of questions

## Output Files

### Image Tasks (text-to-image, image-to-image)
- **Images**: Single output image from nodes with 'images' output

### Video Tasks (all others)
Workflows should produce:
- **Thumbnail**: First image output (from PreviewImage or SaveImage node)
- **Raw Video**: Base video output (SaveVideo node with "raw" in filename_prefix)
- **Upscaled Video**: Enhanced video output (SaveVideo node with "upscaled" in filename_prefix)

## Creating New Workflows

1. Design workflow in ComfyUI UI
2. Export workflow JSON via "Save (API Format)"
3. Replace hardcoded values with placeholders
4. Name file using convention: `workflow_{task_type}.json`
5. Place in this directory
6. Ensure output nodes are properly named (raw/upscaled)

## Example Workflows

- `workflow_image-to-video.json` - Basic image-to-video generation
- `workflow_image-to-talk-video.json` - Talking face video with audio reference

## Notes

- Workflows must be valid ComfyUI API format JSON
- All file paths in placeholders will be replaced with local `/tmp/` paths
- Worker handles file downloads and S3 uploads automatically
- Workflow execution timeout: configurable via `GPU_WORKER_MAX_EXECUTION_TIME`, with fallback to `MCP_TOOL_TIMEOUT` (milliseconds) from `config/mcp.json5`
