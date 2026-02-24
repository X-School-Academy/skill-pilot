"""Split Screen scene type module for video creation"""

import os
from typing import Dict, Any
from ..VideoStyle import VideoStyle

# Import utility functions
from llm import LLM    
from ..video_utils.html2image import capture_image
import subprocess
from tts_service import async_text_to_audio_file





async def create_split_screen_scene(scene: Dict[str, Any], style: VideoStyle, cost_member_id: int = None) -> tuple[str, float]:
    """
    Create a split screen scene video.

    Args:
        scene: Scene data containing:
            - text1: string - first item
            - text2: string - second item
            - voice_over: string
        style: Video style configuration
        cost_member_id: Member ID for cost tracking (None for system cost)

    Returns:
        tuple: (video_path, scene_cost) - Local file path to the generated video and accumulated cost for this scene
    """

    # Extract scene data
    text1 = scene.get("text1", "")
    text2 = scene.get("text2", "")
    voice_over = scene.get("voice_over", "")

    # Track accumulated cost for this scene
    scene_cost = 0.0
    
    if not text1:
        raise ValueError("Split screen scene requires 'text1' field")
    
    if not text2:
        raise ValueError("Split screen scene requires 'text2' field")
    
    if not voice_over:
        raise ValueError("Split screen scene requires 'voice_over' field")
    
    # Create HTML content for split screen display
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    # Determine layout direction based on orientation
    is_landscape = style.width > style.height
    flex_direction = "row" if is_landscape else "column"
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Split Screen Scene</title>
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
        
        .split-container {{
            display: flex;
            flex-direction: {flex_direction};  /* Responsive: row for landscape, column for portrait */
            width: 90%;
            height: 80%;
            gap: calc(var(--padding) * 1.5);
        }}
        
        .split-item {{
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.1);
            border: var(--border-width) solid var(--border-color);
            border-radius: var(--border-radius);
            padding: var(--padding);
            text-align: center;
            box-shadow: var(--box-shadow);
            position: relative;
        }}
        
        .split-item::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: linear-gradient(135deg, var(--accent-color)20, transparent);
            border-radius: var(--border-radius);
            pointer-events: none;
        }}
        
        .split-text {{
            font-size: var(--title-size);
            font-weight: var(--title-weight);
            color: var(--primary-color);
            line-height: var(--line-height);
            word-wrap: break-word;
            z-index: 1;
            position: relative;
        }}
        
        .split-item:first-child {{
            border-left: 4px solid var(--accent-color);
        }}
        
        .split-item:last-child {{
            border-right: 4px solid var(--success-color);
        }}
        
        .vs-separator {{
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            background: var(--accent-color);
            color: white;
            width: 60px;
            height: 60px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: var(--body-size);
            font-weight: bold;
            z-index: 10;
            box-shadow: var(--box-shadow);
        }}
    </style>
</head>
<body>
    <div class="split-container">
        <div class="split-item">
            <div class="split-text">{text1}</div>
        </div>
        <div class="split-item">
            <div class="split-text">{text2}</div>
        </div>
    </div>
    <div class="vs-separator">VS</div>
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
        raise Exception("Failed to capture image for split screen scene")
    
    # Generate audio file using Gemini TTS or fallback to LLM
    tts_cost = 0.0
    try:
        audio_path, tts_cost = await async_text_to_audio_file(
            voice_over,
            voice=style.voice_name,
            format="wav",
            cost_member_id=cost_member_id,
            cost_note="Split screen scene - voice narration"
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        # Fallback to original LLM method
        async with LLM() as llm:
            audio_path, tts_cost = await llm.text_to_audio_file(
                voice_over, 
                voice=style.voice_name,
                cost_member_id=cost_member_id,
                cost_note="Split screen scene - voice narration (fallback MS TTS)"
            )
    
    if not audio_path:
        raise Exception("Failed to generate audio for split screen scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    scene_cost += tts_cost
    
    # Create video by combining image and audio using ffmpeg
    import uuid
    video_filename = f"split_screen_scene_{uuid.uuid4()}.mp4"
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
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except:
        pass  # Ignore cleanup errors

    return video_path, scene_cost
