# Video Creator Update Plan

## Goal

Extend the multi-scene video workflow so it can:

1. accept an `output_path` for all generated artifacts,
2. persist scene images, scene audio, scene videos, the final merged video, and an audit `README.md`,
3. support two new scene types: `host_speech_clip` and `video_clip`,
4. update the `create-multiple-scene-video` skill metadata to the new skill name `create-multiple-scene-video`.

This plan is for approval before implementation.

## Current Code Check

Based on the current code in [video_creator.py](/Users/frankhe/myworks/skill-pilot-ai/core/engine/workflow/video_creator.py), [scene_types/__init__.py](/Users/frankhe/myworks/skill-pilot-ai/core/engine/workflow/scene_types/__init__.py), and [SKILL.md](/Users/frankhe/myworks/skill-pilot-ai/core/skills/system/create-multiple-scene-video/SKILL.md):

- `create_video()` and `merge_scenes_node()` still hardcode `/tmp` for final outputs.
- Scene helpers mostly create temporary files and clean them up after rendering; that conflicts with the new audit requirement to keep scene images/audio/videos.
- The scene registry does not include video-driven scene types yet.
- Existing scene generation is image/html centric, not video-clip centric.
- The `create-multiple-scene-video` skill and its reference docs still expose the old payload contract.
- There is no local `core/bin/cli` entrypoint in this repo. The actual local command wrapper is [tool-cli](/Users/frankhe/myworks/skill-pilot-ai/core/bin/tool-cli), which runs:
  - `uv --directory core/engine run python -m mcp_servers.mcp_to_skills.cli ...`
- The workflow should call local media MCP tools through `core/bin/tool-cli request '<json>'`, not through agent-skill text execution.
- Relevant local media MCP tools already exposed by the engine are:
  - `image_to_talk_video`
  - `video_to_talk_video`
  - `video_lipsync`

## Proposed Output Layout

Use `output_path` as the parent directory, and create a run-specific subdirectory under it to avoid collisions:

```text
{output_path}/{run_id}/
  README.md
  final_video.mp4
  scenes/
    scene_001/
      image.png               # if the scene uses/generated an image
      audio.wav               # if the scene uses/generated audio
      video.mp4               # scene result with audio track
      source_video.mp4        # when the scene starts from a user/local/generated video
      host_image.png          # for host speech clip when applicable
```

If you want all files written directly into `output_path` without a run subdirectory, I can do that, but I recommend a run directory to prevent filename collisions and accidental overwrites.

## Scope

### 1. API and Workflow Parameters

Update [video_creator.py](/Users/frankhe/myworks/skill-pilot-ai/core/engine/workflow/video_creator.py) to:

- add `output_path: str = "/tmp"` to `create_video()`,
- thread `output_path` through the workflow state,
- update `create_multiple_scene_video()` to accept and pass `output_path`,
- ensure final merge output and all intermediate saved artifacts land under the run directory inside `output_path`.

### 2. Artifact Persistence and Audit README

Refactor the workflow so it does not treat generated scene artifacts as disposable temp files when they are part of the requested audit output.

Implementation plan:

- add helpers to create a per-run output directory and per-scene directories,
- save generated images/audio using deterministic scene-based filenames,
- save each rendered scene video in that scene directory,
- save the merged final video in the run root,
- generate a `README.md` that lists:
  - input requirement summary,
  - output resolution and duration target,
  - all scenes in order,
  - each file created and its purpose,
  - whether the scene used generated or provided image/audio/video assets.

### 3. New Scene Type: `host_speech_clip`

Add a new scene type with these supported fields:

- `scene_type: "host_speech_clip"`
- `video_type: "talk_video" | "lipsync"` default `talk_video`
- `host_image_path`
- `host_image_prompt`
- `talking_video_prompt`
- `video_path`
- `voice_over`
- `voice_path`

Planned behavior:

- if `video_path` exists and already has an audio track, use it as the final scene video and only normalize/crop/retime as needed,
- if `video_path` exists but has no audio track:
  - for `talk_video`, generate the talking clip via local MCP tool `video_to_talk_video`,
  - for `lipsync`, generate the talking clip via local MCP tool `video_lipsync`,
- if `video_path` is absent:
  - resolve or generate the host image from `host_image_path` / `host_image_prompt`,
  - for `talk_video`, call local MCP tool `image_to_talk_video` directly with the prepared image and audio,
  - for `lipsync`, regard it as type `talk_video` type
- if `voice_path` is provided, reuse it,
- otherwise generate audio from `voice_over`.

Technical execution details:

- `core/bin/tool-cli` is the correct shell entrypoint. There is no `core/bin/cli`.
- For image-driven talk video generation, use:

```bash
core/bin/tool-cli request '{
  "server_id": "media",
  "tool_name": "image_to_talk_video",
  "arguments": {
    "prompt": "<talking_video_prompt>",
    "image_file": "<host_image_file>",
    "audio_file": "<scene_audio_file>",
    "width": <target_width>,
    "height": <target_height>
  }
}'
```

- For video-driven talk video generation, use:

```bash
core/bin/tool-cli request '{
  "server_id": "media",
  "tool_name": "video_to_talk_video",
  "arguments": {
    "prompt": "<talking_video_prompt>",
    "video_file": "<source_video_file>",
    "audio_file": "<scene_audio_file>",
    "width": <target_width>,
    "height": <target_height>,
    "pingpong": true
  }
}'
```

- For lipsync generation, use:

```bash
core/bin/tool-cli request '{
  "server_id": "media",
  "tool_name": "video_lipsync",
  "arguments": {
    "video_file": "<source_video_file>",
    "audio_file": "<scene_audio_file>",
    "label": "<scene_id>",
    "pingpong": true
  }
}'
```

- The media server implementation in [main.py](/Users/frankhe/myworks/skill-pilot-ai/core/engine/mcp_servers/media/main.py) confirms:
  - `image_to_talk_video(prompt, image_file, audio_file, width, height)`
  - `video_to_talk_video(prompt, video_file, audio_file, width, height, pingpong=True)`
  - `video_lipsync(audio_file, video_file, label=None, pingpong=True)`
- The workflow should invoke these commands with `subprocess.run(..., capture_output=True, text=True)` and parse the JSON/string result into a local file path before saving the scene artifact manifest.
- If `video_type` is `lipsync` but `video_path` is absent, the workflow should explicitly downgrade that branch to the `talk_video` path and call `image_to_talk_video`, because `video_lipsync` requires a real input `video_file` while `image_to_talk_video` accepts an image directly.

### 4. New Scene Type: `video_clip`

Add a new scene type with these fields:

- `scene_type: "video_clip"`
- `video_path`
- `voice_over`
- `voice_path`

Planned behavior:

- require `video_path`,
- reuse `voice_path` if provided, otherwise generate from `voice_over`,
- probe source video duration and audio duration,
- if the source video is longer than the audio, keep the scene length equal to the video duration,
- if the audio is longer than the video, retime the video so the final scene length becomes `audio duration + 2s` and add the trailing silence requirement there.

Technical execution details:

- `video_clip` does not use a media MCP generator unless later required. It should use local ffprobe/ffmpeg only.
- The implementation should:
  - probe source width/height, frame rate, duration, and whether an audio stream exists,
  - if `voice_path`/generated scene audio is present, map that audio onto the final scene output,
  - if `audio_duration > video_duration`, slow the video with `setpts` so output duration becomes `audio_duration + 2`,
  - if `video_duration >= audio_duration`, keep the original video duration,
  - normalize resolution with scale+crop,
  - normalize output fps to `30`.

### 5. Resolution, Duration, and Frame-Rate Normalization

Add shared media utilities for:

- `ffprobe` resolution detection,
- `ffprobe` audio-track detection,
- `ffprobe` duration detection,
- ffmpeg scale-and-crop to target resolution,
- video retiming to match required scene duration,
- audio padding with `2s` silence where required,
- final scene normalization to `30 fps` before merge.

This should live in workflow-local helpers so both new scene types can reuse the same logic, and merge behavior stays consistent.

Planned helper details:

- Add a shared ffprobe helper that returns:
  - width
  - height
  - fps
  - duration
  - whether an audio stream exists
- Add a shared ffmpeg normalize helper with a filter like:

```text
scale=<target_w>:<target_h>:force_original_aspect_ratio=increase,crop=<target_w>:<target_h>,fps=30
```

- Add a helper for audio padding to `audio_duration + 2s` when required, for example with:

```text
apad=pad_dur=2
```

- Add a helper for video retiming:

```text
setpts=<speed_factor>*PTS
```

- Merge should force each scene clip to a consistent `30 fps` stream before concat so final output is stable.

### 6. Scene Registry and Planning Prompt

Update the scene system so the planner can emit the new scene types.

Planned files:

- [video_creator.py](/Users/frankhe/myworks/skill-pilot-ai/core/engine/workflow/video_creator.py)
- [scene_types/__init__.py](/Users/frankhe/myworks/skill-pilot-ai/core/engine/workflow/scene_types/__init__.py)
- new scene modules, likely:
  - `core/engine/workflow/scene_types/host_speech_clip.py`
  - `core/engine/workflow/scene_types/video_clip.py`

Planner prompt updates:

- document both new scene types in the allowed-scene JSON schema,
- define field precedence rules exactly as requested,
- clarify that `host_image_path` overrides `host_image_prompt`,
- clarify that `video_path` with an existing audio track short-circuits other generation steps.

### 7. Skill Rename

Update the skill metadata under [SKILL.md](/Users/frankhe/myworks/skill-pilot-ai/core/skills/system/create-multiple-scene-video/SKILL.md) so the skill name becomes `create-multiple-scene-video`.

Planned changes:

- update frontmatter `name`,
- update title/body text to reflect the multi-scene naming,
- update the reference doc wording under [api-invoke.md](/Users/frankhe/myworks/skill-pilot-ai/core/skills/system/create-multiple-scene-video/references/api-invoke.md),
- rename the API command/route to `create_multiple_scene_video`.

## Implementation Order

1. Add `output_path` support and run-directory creation in the workflow.
2. Add shared saved-artifact utilities and audit README generation.
3. Add shared media probe/normalize helpers for resolution, duration, fps, and audio handling.
4. Implement `video_clip`.
5. Implement `host_speech_clip`.
6. Register both scene types and update the planner prompt/schema.
7. Update the skill metadata/docs to `create-multiple-scene-video`.
8. Run targeted validation on the workflow module and new scene modules.

## Validation Plan

Before reporting completion, I will validate with:

- Python syntax checks for all touched workflow files,
- a targeted dry check of scene-plan generation strings,
- at least one focused local flow test per new scene type if the required media tools are available in this repo runtime,
- confirmation that the output directory contains:
  - scene images where applicable,
  - scene audio files where applicable,
  - per-scene videos,
  - final merged video,
  - `README.md`.

## Assumptions To Confirm

These are the assumptions I plan to implement unless you want them changed before coding:

1. `output_path` means a parent directory, and the workflow should create a unique run subdirectory inside it.
2. The skill rename applies to skill metadata and docs, not necessarily the folder path.
3. The API endpoint/command is renamed to `create_multiple_scene_video`.
4. For `host_speech_clip`, if `video_path` is absent, I should build the best local host-video path from existing media tools already present in this repo instead of introducing a new remote dependency.
