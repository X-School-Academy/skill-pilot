"""Image With Caption scene type module for video creation"""

import os
from typing import Dict, Any
from ..VideoStyle import VideoStyle
import uuid

# Import utility functions
from llm import LLM    
from image_service import generate_image_from_prompt
from ..video_utils.html2image import capture_image
import subprocess
from tts_service import async_text_to_audio_file
import base64





async def create_image_with_caption_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """
    Create an image with caption scene video.

    Args:
        scene: Scene data containing:
            - image_prompt: string - AI prompt which will be used to create the image
            - image_path: string - local file path to a provided image
            - text: string - caption of the image
            - voice_over: string
        style: Video style configuration

    Returns:
        Local file path to the generated video
    """

    # Extract scene data
    image_prompt = scene.get("image_prompt", "")
    image_path = scene.get("image_path", "")
    caption_text = scene.get("text", "")
    voice_over = scene.get("voice_over", "")

    width = style.width
    height = style.height

    min_length = min(width, height)
    image_size = min_length * 0.75  # Use 75% of the minimum dimension for image size

    has_image_prompt = bool(image_prompt)
    has_image_path = bool(image_path)

    if has_image_prompt == has_image_path:
        raise ValueError(
            "Image with caption scene requires exactly one of 'image_prompt' or 'image_path'"
        )

    if has_image_path and not os.path.isfile(image_path):
        raise ValueError(f"Image with caption scene image_path does not exist: {image_path}")
    
    if not caption_text:
        raise ValueError("Image with caption scene requires 'text' field")
    
    if not voice_over:
        raise ValueError("Image with caption scene requires 'voice_over' field")
    
    generated_image_path = image_path
    should_cleanup_generated_image = False
    if has_image_prompt:
        try:
            generated_image_path = await generate_image_from_prompt(
                image_prompt,
                style='icon',
            )
            if not generated_image_path:
                raise Exception("Failed to generate image from prompt")

            should_cleanup_generated_image = True
        except Exception as e:
            raise Exception(f"Failed to generate image: {str(e)}")

    scene['image_url'] = generated_image_path
    
    # Convert image to base64 for embedding in HTML
    with open(generated_image_path, "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode('utf-8')
        img_mime_type = "image/png" if generated_image_path.endswith('.png') else "image/jpeg"
    
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
        
        .main-image {{
            max-width: 85%;
            max-height: 85%;
            width: {image_size}px;  /* Use calculated image size */
            height: {image_size}px;  /* Use calculated image size */
            object-fit: contain;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
        }}
        
        .caption-container {{
            width: 100%;
            text-align: center;
            padding: 0;
            margin-top: 0;
        }}
        
        .caption-text {{
            font-size: var(--subtitle-size);
            font-weight: var(--title-weight);
            color: var(--primary-color);
            line-height: var(--line-height);
            word-wrap: break-word;
            font-family: var(--primary-font);
        }}
    </style>
</head>
<body>

    <img src="data:{img_mime_type};base64,{img_base64}" alt="Generated Image" class="main-image">

    <div class="caption-container">
        <div class="caption-text">{caption_text}</div>
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
        raise Exception("Failed to capture composite image for image with caption scene")
    
    # Generate audio file using Gemini TTS or fallback to LLM
    try:
        audio_path = await async_text_to_audio_file(
            voice_over,
            voice=style.voice_name,
            format="wav",
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        # Fallback to original LLM method
        async with LLM() as llm:
            audio_path = await llm.text_to_audio_file(
                voice_over, 
                voice=style.voice_name,
            )
    
    if not audio_path:
        raise Exception("Failed to generate audio for image with caption scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    # Create video by combining image and audio using ffmpeg
    video_filename = f"image_caption_scene_{uuid.uuid4()}.mp4"
    if caption_text == '&nbsp;':
        video_filename = f"image_scene_{uuid.uuid4()}.mp4"
    
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
        if should_cleanup_generated_image and os.path.exists(generated_image_path):
            os.remove(generated_image_path)
        if os.path.exists(composite_image_path):
            os.remove(composite_image_path)
        if os.path.exists(audio_path):
            os.remove(audio_path)
    except:
        pass  # Ignore cleanup errors

    return video_path
