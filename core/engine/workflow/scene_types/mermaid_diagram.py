"""Mermaid Diagram scene type module for video creation"""

import os
import subprocess
from pathlib import Path
import uuid
from typing import Dict, Any
from ..VideoStyle import VideoStyle
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage
import re
from logger import log, error
from .shared import get_or_create_voice_audio

# Import utility functions
from ..video_utils.html2image import capture_image


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MERMAID_CLI = str(REPO_ROOT / "core" / "bin" / "mmdc")


async def create_mermaid_diagram_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """
    Create a mermaid diagram scene video.

    Args:
        scene: Scene data containing:
            - diagram_type: string - flowchart, sequenceDiagram, classDiagram, etc.
            - description: string - detail of the diagram for AI to create mermaid code
            - text: string - caption of the diagram
            - voice_over: string
        style: Video style configuration

    Returns:
        Local file path to the generated video
    """
    
    # Extract scene data
    diagram_type = scene.get("diagram_type", "flowchart")
    description = scene.get("description", "")
    caption_text = scene.get("text", "")
    voice_over = scene.get("voice_over", "")
    voice_path = scene.get("voice_path", "")
    
    if not description:
        raise ValueError("Mermaid diagram scene requires 'description' field")
    
    if not voice_over:
        raise ValueError("Mermaid diagram scene requires 'voice_over' field")
    
    # Prefer the repo-managed Mermaid CLI wrapper over a global install.
    mermaid_cli = os.environ.get("MERMAID_CLI", DEFAULT_MERMAID_CLI)

    # Generate mermaid diagram code using LLM with retry logic for syntax errors
    svg_content = await generate_mermaid_image_with_retry(diagram_type, description, mermaid_cli)
    
    
    # Create HTML content with SVG diagram
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mermaid Diagram Scene</title>
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
            overflow: hidden;
            gap: calc(var(--line-height) * 1em);
        }}
        
        .diagram-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 80%;
            height: 80%;
            max-width: calc(var(--video-width) * 0.8);
            max-height: calc(var(--video-height) * 0.8);
            position: relative;
        }}
        
        .mermaid-svg {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: var(--border-radius);
            box-shadow: var(--box-shadow);
            background: white;
            padding: 20px;
        }}
        
        .mermaid-svg svg {{
            width: 100%;
            height: 100%;
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
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
    <div class="diagram-container">
        <div class="mermaid-svg">
{svg_content}
        </div>
    </div>
    {f'<div class="caption-container"><div class="caption-text">{caption_text}</div></div>' if caption_text else ''}
</body>
</html>
"""
    
    # Capture image from HTML using workflow.video_utils
    is_horizontal = style.width > style.height
    composite_image_path = await capture_image(
        html_content,
        isHorizontal=is_horizontal,
        view_width=style.width,
        view_height=style.height
    )
    
    if not composite_image_path:
        raise Exception("Failed to capture composite image for mermaid diagram scene")
    
    audio_path, should_cleanup_audio = await get_or_create_voice_audio(
        voice_over,
        voice_path,
        style.voice_name,
    )
    
    if not audio_path:
        raise Exception("Failed to generate audio for mermaid diagram scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    # Create video by combining image and audio using ffmpeg
    video_filename = f"mermaid_diagram_scene_{uuid.uuid4()}.mp4"
    video_path = f"/tmp/{video_filename}"

    # save html_content to a temporary file for debugging
    html_temp_path = f"/tmp/mermaid_diagram_scene_{uuid.uuid4()}.html"
    with open(html_temp_path, "w") as f:
        f.write(html_content)
    log(f"HTML content saved to {html_temp_path} for debugging")
    
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
        if should_cleanup_audio and os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(html_temp_path):
            os.remove(html_temp_path)
    except:
        pass  # Ignore cleanup errors

    return video_path


async def generate_mermaid_image_with_retry(diagram_type: str, description: str, mermaid_cli: str, max_retries: int = 3) -> str:
    """
    Generate mermaid code with retry logic for syntax errors.

    Args:
        diagram_type: Type of diagram (flowchart, sequenceDiagram, etc.)
        description: Description of what the diagram should show
        mermaid_cli: Path to mermaid CLI tool
        max_retries: Maximum number of retries for syntax errors

    Returns:
        SVG content as string
    """
    
    # Initialize LLM model
    model = init_chat_model(
        f"azure_openai:{os.environ.get('AZURE_OPENAI_CHAT_MODEL_NAME', 'gpt-4.1')}",
        azure_deployment=os.environ.get("AZURE_OPENAI_CHAT_MODEL_NAME", "gpt-4.1"),
        azure_endpoint=os.environ.get("AZURE_OPENAI_CHAT_ENDPOINT"),
        api_version=os.environ.get("AZURE_OPENAI_CHAT_MODEL_API_VERSION"),
        api_key=os.environ.get("AZURE_OPENAI_CHAT_API_KEY"),
        max_retries=3,
        temperature=0.7,
        max_tokens=4096 * 2,
    )
    
    diagram_prompt = f"""
    Create a {diagram_type} diagram using Mermaid syntax for the following description:
    {description}
    
    Return only the Mermaid diagram code without any explanation or markdown formatting.
    Make sure the diagram is valid {diagram_type} syntax.
    """
    
    messages = [HumanMessage(content=diagram_prompt)]

    for attempt in range(max_retries):
        try:
            # Generate mermaid code
            response = await model.ainvoke(messages)
            mermaid_code = response.content.strip()

            if not mermaid_code:
                raise Exception("Failed to generate mermaid diagram code")

            # Try to generate SVG - this will fail if there are syntax errors
            svg_content = await generate_svg_from_mermaid(mermaid_code, mermaid_cli)

            # If we get here, the mermaid code is valid
            return svg_content

        except Exception as e:
            if attempt == max_retries - 1:
                raise Exception(f"Failed to generate mermaid diagram after {max_retries} attempts: {str(e)}")

            # Add error to conversation for retry
            error_message = f"The mermaid code you generated has syntax errors: {str(e)}. Please fix the syntax and generate a valid mermaid diagram."
            messages.append(HumanMessage(content=error_message))

    raise Exception("Failed to generate valid mermaid code")


async def generate_svg_from_mermaid(mermaid_code: str, mermaid_cli: str) -> str:
    """
    Generate SVG content from mermaid code using mmdc command.
    
    Args:
        mermaid_code: Valid mermaid code
        mermaid_cli: Path to mermaid CLI tool
        
    Returns:
        SVG content as string
    """

    try:
        # Use mmdc with stdin/stdout
        cmd = [mermaid_cli, "-i", "-", "-e", "svg", "-o", "-"]
        
        result = subprocess.run(
            cmd,
            input=mermaid_code,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            svg_output = result.stdout
            # Replace any style attribute content with just background-color: white
            # This ensures the SVG scales properly within our container without size constraints
            svg_output = re.sub(
                r'style="[^"]*"',
                'style="background-color: white;"',
                svg_output
            )
            return svg_output
        else:
            raise Exception(f"Failed to generate SVG: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        raise Exception("Timeout while generating SVG from mermaid code")
    except Exception as e:
        raise Exception(f"Error generating SVG: {str(e)}")
