"""Bullet List scene type module for video creation"""

import os
import math
from typing import Dict, Any, List
from ..VideoStyle import VideoStyle

# Import utility functions
from ..video_utils.html2image import capture_image
import subprocess
from .shared import get_or_create_voice_audio


async def create_bullet_list_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """
    Create a bullet list scene video.

    Args:
        scene: Scene data containing:
            - items: list of strings - item text shown in the screen
            - voice_over: string
        style: Video style configuration

    Returns:
        Local file path to the generated video
    """

    # Extract scene data
    items = scene.get("items", [])

    if not isinstance(items, list):
        raise ValueError("Bullet list scene 'items' must be a list")
    else:
        # fix a json format error from gemini
        first_item = items[0] if items else ""
        if isinstance(first_item, dict):
            items = [item.get("text", "") for item in items]
    voice_over = scene.get("voice_over", "")
    voice_path = scene.get("voice_path", "")
    
    if not items:
        raise ValueError("Bullet list scene requires 'items' field")
    
    if not voice_over:
        raise ValueError("Bullet list scene requires 'voice_over' field")
    
    # Generate HTML for bullet points
    bullet_items_html = ""
    for item in items:
        bullet_items_html += f"<li class='bullet-item'>{item}</li>\n"

    item_count = len(items)
    available_height = max(style.height - 120, 200)
    base_font_size = style.bullet_font_size
    base_gap = style.card_gap
    base_vertical_padding = 40
    base_horizontal_padding = 40
    base_left_padding = 100
    base_icon_size = base_font_size + 4
    base_icon_left = 36

    estimated_item_height = (base_font_size * 1.4) + (base_vertical_padding * 2)
    estimated_total_height = (
        estimated_item_height * item_count
    ) + (base_gap * max(item_count - 1, 0))
    scale = 1.0
    if estimated_total_height > available_height:
        scale = max(0.55, available_height / estimated_total_height)

    bullet_font_size = max(22, math.floor(base_font_size * scale))
    bullet_gap = max(10, math.floor(base_gap * scale))
    bullet_vertical_padding = max(16, math.floor(base_vertical_padding * scale))
    bullet_horizontal_padding = max(20, math.floor(base_horizontal_padding * scale))
    bullet_left_padding = max(
        bullet_horizontal_padding + 42,
        math.floor(base_left_padding * scale),
    )
    bullet_radius = max(style.border_radius, math.floor(style.border_radius * 3 * scale))
    bullet_border_width = max(4, math.floor(style.card_border_width * scale))
    bullet_icon_size = max(bullet_font_size, math.floor(base_icon_size * scale))
    bullet_icon_left = max(22, math.floor(base_icon_left * scale))
    
    # Create HTML content for the bullet list display
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bullet List Scene</title>
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
            background: linear-gradient(135deg, var(--bg-color) 0%, #2d3748 100%);
            font-family: var(--primary-font);
            color: var(--primary-color);
            display: flex;
            flex-direction: column;
            justify-content: center;
            padding: 60px 40px;
        }}
        
        .list-container {{
            width: 100%;
            text-align: left;
            max-height: 100%;
            overflow: hidden;
        }}
        
        .bullet-list {{
            list-style: none;
            padding: 0;
            display: flex;
            flex-direction: column;
            gap: {bullet_gap}px;
        }}
        
        .bullet-item {{
            font-size: {bullet_font_size}px;
            font-weight: 500;
            color: var(--primary-color);
            line-height: 1.4;
            position: relative;
            padding: {bullet_vertical_padding}px {bullet_horizontal_padding}px {bullet_vertical_padding}px {bullet_left_padding}px;
            background: var(--card-bg);
            border-radius: {bullet_radius}px;
            border-left: {bullet_border_width}px solid var(--accent-color);
            backdrop-filter: var(--backdrop-blur);
            word-wrap: break-word;
            text-align: left;
        }}
        
        .bullet-item::before {{
            content: "✦";
            color: var(--accent-color);
            font-size: {bullet_icon_size}px;
            position: absolute;
            left: {bullet_icon_left}px;
            top: 50%;
            transform: translateY(-50%);
            text-shadow: 0 0 var(--glow-intensity) var(--accent-color);
        }}
    </style>
</head>
<body>
    <div class="list-container">
        <ul class="bullet-list">
            {bullet_items_html}
        </ul>
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
        raise Exception("Failed to capture image for bullet list scene")
    
    audio_path, should_cleanup_audio = await get_or_create_voice_audio(
        voice_over,
        voice_path,
        style.voice_name,
    )

    if not audio_path:
        raise Exception("Failed to generate audio for bullet list scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    # Create video by combining image and audio using ffmpeg
    import uuid
    video_filename = f"bullet_list_scene_{uuid.uuid4()}.mp4"
    video_path = f"/tmp/{video_filename}"
    
    # Use ffmpeg to create video from image and audio with PCM audio (no AAC priming samples)
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
