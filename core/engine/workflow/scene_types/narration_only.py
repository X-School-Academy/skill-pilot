"""Narration Only scene type module for video creation"""

import os
from typing import Dict, Any
from ..VideoStyle import VideoStyle
import uuid

from llm import LLM
from ..video_utils.html2image import capture_image
import subprocess
from tts_service import async_text_to_audio_file

async def create_narration_only_scene(scene: Dict[str, Any], style: VideoStyle, cost_member_id: int = None) -> tuple[str, float]:
    """
    Args:
        scene: Scene data containing:
            - voice_over: string
        style: Video style configuration
        cost_member_id: Member ID for cost tracking (None for system cost)

    Returns:
        tuple: (video_path, scene_cost) - Local file path to the generated video and accumulated cost for this scene
    """

    voice_over = scene.get("voice_over", "")

    # Track accumulated cost for this scene
    scene_cost = 0.0
    
    if not voice_over:
        raise ValueError("Image with caption scene requires 'voice_over' field")
    # Create HTML content with image and caption
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image With Caption Scene</title>
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
            background-image: var(--bg-gradient);
            font-family: var(--primary-font);
            color: var(--primary-color);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: var(--margin);
            font-size: var(--base-font-size);
            line-height: var(--line-height);
            gap: calc(var(--line-height) * 1em);
        }}
        
    </style>
</head>
<body>

</body>
</html>
"""
    
    # Capture image from HTML
    is_horizontal = style.width > style.height
    composite_image_path = await capture_image(
        html_content,
        isHorizontal=is_horizontal,
        view_width=style.width,
        view_height=style.height
    )
    
    if not composite_image_path:
        raise Exception("Failed to capture composite image for narration only scene")
    
    # Generate audio file using Gemini TTS or fallback to LLM
    tts_cost = 0.0
    try:
        audio_path, tts_cost = await async_text_to_audio_file(
            voice_over,
            voice=style.voice_name,
            format="wav",
            cost_member_id=cost_member_id,
            cost_note="Narration only scene - voice narration"
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        # Fallback to original LLM method
        async with LLM() as llm:
            audio_path, tts_cost = await llm.text_to_audio_file(
                voice_over, 
                voice=style.voice_name,
                cost_member_id=cost_member_id,
                cost_note="Narration only scene - voice narration (fallback MS TTS)"
            )
    
    if not audio_path:
        raise Exception("Failed to generate audio for narration only scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    scene_cost += tts_cost
    
    # Create video by combining image and audio using ffmpeg
    video_filename = f"narration_only_scene_{uuid.uuid4()}.mp4"

    video_path = f"/tmp/{video_filename}"
    
    # Use ffmpeg to create video from image and audio
    ffmpeg_cmd = [
        "ffmpeg", "-y",  # -y to overwrite output file
        "-loop", "1",  # Loop the image
        "-i", composite_image_path,  # Input composite image
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
        if os.path.exists(composite_image_path):
            os.remove(composite_image_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except:
        pass  # Ignore cleanup errors

    return video_path, scene_cost
