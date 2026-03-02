---
name: media-html5-video-clip
description: "Render an HTML/CSS/JS animation into an MP4 clip using a headless browser."
---

Args:
    html_file: HTML file_id from /upload_file that defines video_started()/video_ended() helpers.
    width: Viewport width (px) for the recorded clip.
    height: Viewport height (px) for the recorded clip.
    animate_time: Maximum duration in seconds to wait for the animation to finish.

Returns:
    Recorded video clip as a URL in MP4 format.

Example HTML snippet:
```html
<!DOCTYPE html>
<html>
<head>
  <style>
    :root { --video-width: 1080px; --video-height: 1920px; }
    body { width: var(--video-width); height: var(--video-height); margin: 0;
           display: flex; align-items: center; justify-content: center;
           font-family: 'Inter', sans-serif; background: #020617; color: white; }
    .card { opacity: 0; font-size: 64px; transition: opacity 1s ease; }
    body.ready .card { opacity: 1; }
  </style>
</head>
<body>
  <div class="card">Launch Day</div>
  <script>
    let started = false; let ended = false;
    function video_started() {
      if (!started) {
        started = true;
        document.body.classList.add('ready');
        setTimeout(() => { ended = true; }, 4000);
      }
      return started;
    }
    function video_ended() { return ended; }
    setTimeout(video_started, 200);
  </script>
</body>
</html>
```

## Usage
Call the local MCP bridge shell wrapper:

```bash
core/bin/tool-cli request '{"server_id": "media", "tool_name": "html5_video_clip", "arguments": {}}'
```

## Arguments Schema
```json
{
  "properties": {
    "html_file": {
      "type": "string"
    },
    "width": {
      "type": "integer"
    },
    "height": {
      "type": "integer"
    },
    "animate_time": {
      "default": 10.0,
      "type": "number"
    }
  },
  "required": [
    "html_file",
    "width",
    "height"
  ],
  "type": "object"
}
```
