"""Icon Grid scene type module for video creation"""

import os
import base64
import asyncio
from typing import Dict, Any, List
from ..VideoStyle import VideoStyle

# Import utility functions
from llm import LLM    
from image_service import generate_image_from_prompt
from ..video_utils.html2image import capture_image
import subprocess
from tts_service import async_text_to_audio_file





async def create_icon_grid_scene(scene: Dict[str, Any], style: VideoStyle, cost_member_id: int = None) -> tuple[str, float]:
    """
    Create an icon grid scene video.

    Args:
        scene: Scene data containing:
            - icons: list of dicts with:
                - image_prompt: string - use to create the icon image with AI
                - text: string - the caption of the image
            - voice_over: string
        style: Video style configuration
        cost_member_id: Member ID for cost tracking (None for system cost)

    Returns:
        tuple: (video_path, scene_cost) - Local file path to the generated video and accumulated cost for this scene
    """

    # Extract scene data
    icons = scene.get("icons", [])
    voice_over = scene.get("voice_over", "")

    # Track accumulated cost for this scene
    scene_cost = 0.0
    
    if not icons:
        raise ValueError("Icon grid scene requires 'icons' field")
    
    if len(icons) > 4:
        raise ValueError("Icon grid scene supports maximum 4 icons")
    
    if not voice_over:
        raise ValueError("Icon grid scene requires 'voice_over' field")
    
    # Generate all icon images concurrently
    icon_tasks = []
    for i, icon in enumerate(icons):
        prompt = icon.get("image_prompt", "")
        if not prompt:
            raise ValueError(f"Icon {i+1} missing 'prompt' field")
        icon_tasks.append(generate_image_from_prompt(
            prompt,
            style='icon',
            cost_member_id=cost_member_id,
            cost_note=f"Icon grid scene - icon {i+1} image generation"
        ))

    try:
        icon_results = await asyncio.gather(*icon_tasks)
        icon_image_paths = []
        # Upload icon images to S3 and add URLs to scene data
        for i, (icon, (image_path, image_cost)) in enumerate(zip(icons, icon_results)):
            icon_image_paths.append(image_path)
            if image_path:
                icon['image_url'] = image_path
            scene_cost += image_cost
    except Exception as e:
        raise Exception(f"Failed to generate icon images: {str(e)}")
    
    # Convert images to base64 for embedding in HTML
    icon_images_base64 = []
    for i, image_path in enumerate(icon_image_paths):
        if not image_path:
            raise Exception(f"Failed to generate icon image {i+1}")
        
        with open(image_path, "rb") as img_file:
            img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
            img_mime_type = "image/png" if image_path.endswith('.png') else "image/jpeg"
            icon_images_base64.append((img_base64, img_mime_type))
    
    # Generate HTML for icon grid
    icon_items_html = ""
    for i, (icon, (img_base64, img_mime_type)) in enumerate(zip(icons, icon_images_base64)):
        text = icon.get("text", "")
        icon_items_html += f"""
        <div class="icon-item">
            <div class="icon-image-container">
                <img src="data:{img_mime_type};base64,{img_base64}" alt="Icon {i+1}" class="icon-image">
            </div>
            <div class="icon-text">{text}</div>
        </div>
        """
    
    # Create HTML content for the icon grid display
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    # Determine grid layout based on number of icons and orientation
    is_landscape = style.width > style.height
    
    if is_landscape:
        # Landscape: prefer horizontal layout
        if len(icons) <= 2:
            grid_columns = len(icons)  # Single row for 1-2 icons
            grid_rows = 1
        elif len(icons) <= 4:
            grid_columns = 2  # 2x2 grid for 3-4 icons
            grid_rows = 2
        else:
            grid_columns = 3  # 3 columns for 5+ icons
            grid_rows = (len(icons) + 2) // 3
    else:
        # Portrait: prefer vertical layout
        if len(icons) <= 2:
            grid_columns = 1  # Single column for better mobile experience
            grid_rows = len(icons)
        else:
            grid_columns = 2  # Max 2 columns for 3-4 icons
            grid_rows = (len(icons) + 1) // 2
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Icon Grid Scene</title>
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
        
        .grid-container {{
            display: grid;
            grid-template-columns: repeat({grid_columns}, 1fr);
            grid-template-rows: repeat({grid_rows}, 1fr);
            gap: var(--padding);
            width: 80%;
            max-width: 800px;
        }}
        
        .icon-item {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: flex-start;
            text-align: center;
            padding: var(--padding);
        }}
        
        .icon-image-container {{
            width: 100%;
            aspect-ratio: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: calc(var(--body-size) * var(--line-height));
            position: relative;
        }}
        
        .icon-image {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            border-radius: var(--border-radius);
        }}
        
        .icon-text {{
            font-size: var(--body-size);
            font-weight: var(--body-weight);
            color: var(--primary-color);
            line-height: var(--line-height);
            word-wrap: break-word;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="grid-container">
        {icon_items_html}
    </div>
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
        raise Exception("Failed to capture composite image for icon grid scene")
    
    # Generate audio file using Gemini TTS or fallback to LLM
    tts_cost = 0.0
    try:
        audio_path, tts_cost = await async_text_to_audio_file(
            voice_over,
            voice=style.voice_name,
            format="wav",
            cost_member_id=cost_member_id,
            cost_note="Icon grid scene - voice narration"
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        # Fallback to original LLM method
        async with LLM() as llm:
            audio_path, tts_cost = await llm.text_to_audio_file(
                voice_over, 
                voice=style.voice_name,
                cost_member_id=cost_member_id,
                cost_note="Icon grid scene - voice narration (fallback MS TTS)"
            )

    if not audio_path:
        raise Exception("Failed to generate audio for icon grid scene")

    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    scene_cost += tts_cost
    
    # Create video by combining image and audio using ffmpeg
    import uuid
    video_filename = f"icon_grid_scene_{uuid.uuid4()}.mp4"
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
        # Clean up generated icon images
        for image_path in icon_image_paths:
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
        if os.path.exists(composite_image_path):
            os.remove(composite_image_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except:
        pass  # Ignore cleanup errors

    return video_path, scene_cost
