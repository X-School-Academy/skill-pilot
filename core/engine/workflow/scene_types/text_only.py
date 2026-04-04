"""Text Only scene type module for video creation"""

import os
from typing import Dict, Any
from ..VideoStyle import VideoStyle

# Import utility functions
from ..video_utils.html2image import capture_image
import subprocess
from .shared import get_or_create_voice_audio, render_markdown_html


async def create_text_only_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """
    Create a text-only scene video.

    Args:
        scene: Scene data containing:
            - text: string - shown in the screen
            - voice_over: string
        style: Video style configuration

    Returns:
        Local file path to the generated video
    """

    # Extract scene data
    text = scene.get("text", "")
    voice_over = scene.get("voice_over", "")
    voice_path = scene.get("voice_path", "")

    if not text:
        raise ValueError("Text-only scene requires 'text' field")
    
    if not voice_over:
        raise ValueError("Text-only scene requires 'voice_over' field")

    text_html = render_markdown_html(text)
    
    # Create HTML content for the text display
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Text Only Scene</title>
    <style>
        :root {{
{css_vars_str}
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            width: var(--video-width);
            height: var(--video-height);
            background: var(--bg-color);
            font-family: var(--primary-font);
            color: var(--primary-color);
            display: flex;
            align-items: center;
            justify-content: center;
            padding: var(--margin);
        }}
        
        .text-container {{
            max-width: 80%;
            text-align: left;
            word-wrap: break-word;
            line-height: var(--line-height);
        }}
        
        .main-text {{
            font-size: var(--title-size);
            font-weight: var(--title-weight);
            text-align: center;
            color: var(--primary-color);
        }}

        .main-text > :first-child {{
            margin-top: 0;
        }}

        .main-text > :last-child {{
            margin-bottom: 0;
        }}

        .main-text p,
        .main-text li {{
            font-size: var(--title-size);
            font-weight: var(--title-weight);
        }}

        .main-text ul,
        .main-text ol {{
            display: inline-block;
            text-align: left;
            padding-left: 1.2em;
            margin: 0.5em auto;
        }}

        .main-text strong {{
            color: var(--accent-color);
        }}
    </style>
</head>
<body>
    <div class="text-container">
        <div class="main-text">{text_html}</div>
    </div>
</body>
</html>
"""
    
    # Capture image from HTML
    is_horizontal = style.width > style.height
    image_path = await capture_image(
        html_content,
        isHorizontal=is_horizontal,
        view_width=style.width,
        view_height=style.height
    )
    
    if not image_path:
        raise Exception("Failed to capture image for text-only scene")
    
    audio_path, should_cleanup_audio = await get_or_create_voice_audio(
        voice_over,
        voice_path,
        style.voice_name,
    )

    if not audio_path:
        raise Exception("Failed to generate audio for text-only scene")

    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    # Create video by combining image and audio using ffmpeg
    import uuid
    video_filename = f"text_only_scene_{uuid.uuid4()}.mp4"
    video_path = f"/tmp/{video_filename}"
    
    # Use ffmpeg to create video from image and audio
    ffmpeg_cmd = [
        "ffmpeg", "-y",  # -y to overwrite output file
        "-loop", "1",  # Loop the image
        "-i", image_path,  # Input image
        "-i", audio_path,  # Input audio
        "-c:v", "libx264",  # Video codec
        "-crf", "18",
        "-c:a", "aac",  # PCM audio codec (no priming samples)
        "-pix_fmt", "yuv420p",  # Pixel format for compatibility
        "-shortest",  # End when shortest input ends (audio)
        "-r", "30",  # Frame rate
        video_path
    ]
    
    try:
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise Exception(f"FFmpeg failed: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise Exception("FFmpeg timeout during video creation")
    except Exception as e:
        raise Exception(f"Error running FFmpeg: {str(e)}")
    
    # Return the temporary video file path (don't upload to S3 here)
    if not os.path.exists(video_path):
        raise Exception("Video file was not created successfully")
    
    # Clean up temporary files (keep the video file)
    try:
        if os.path.exists(image_path):
            os.remove(image_path)
        if should_cleanup_audio and os.path.exists(audio_path):
            os.remove(audio_path)
    except:
        pass  # Ignore cleanup errors

    return video_path
