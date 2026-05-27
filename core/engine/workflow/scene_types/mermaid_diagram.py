"""Mermaid Diagram scene type module for video creation"""

import re
import html
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional
import uuid

from langchain_core.messages import AIMessage, HumanMessage

from logger import log, error
from ..VideoStyle import VideoStyle
from ..llm_adapter import WorkflowLLMAdapter
from .shared import get_or_create_voice_audio, render_markdown_html

# Import utility functions
from ..video_utils.html2image import capture_image


REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_MERMAID_CLI = str(REPO_ROOT / "core" / "bin" / "mmdc")
DEFAULT_MERMAID_THEME = os.environ.get("MERMAID_THEME", "neutral")
DEFAULT_MERMAID_BACKGROUND = os.environ.get("MERMAID_BACKGROUND", "white")


class MermaidRenderError(Exception):
    """Raised when Mermaid CLI fails to render the generated Mermaid code."""

    def __init__(self, message: str, mermaid_code: str, cli_error: str):
        super().__init__(message)
        self.mermaid_code = mermaid_code
        self.cli_error = cli_error


def _diagram_generation_constraints(diagram_type: str) -> str:
    constraints = [
        "Return only Mermaid code.",
        "Do not wrap the answer in markdown fences or backticks.",
        "Return exactly one Mermaid diagram.",
    ]
    if diagram_type == "mindmap":
        constraints.append(
            "For mindmap syntax, use exactly one root node in the form root((...)) followed by indented children."
        )
    return "\n".join(f"- {constraint}" for constraint in constraints)


def _build_mermaid_fix_prompt(diagram_type: str, mermaid_code: str, cli_error: str) -> str:
    return (
        "The Mermaid CLI failed to render the diagram you generated.\n\n"
        "Fix the Mermaid code and return only corrected Mermaid code.\n\n"
        "Constraints:\n"
        f"{_diagram_generation_constraints(diagram_type)}\n\n"
        "Current Mermaid code:\n"
        f"{mermaid_code}\n\n"
        "Mermaid CLI error:\n"
        f"{cli_error}"
    )


def _strip_markdown_fences(content: str) -> str:
    fenced_blocks = re.findall(r"```(?:mermaid)?\s*(.*?)```", content, flags=re.DOTALL | re.IGNORECASE)
    if fenced_blocks:
        return fenced_blocks[0].strip()
    return content.replace("```mermaid", "").replace("```", "").strip()


def _extract_single_diagram_block(mermaid_code: str, diagram_type: str) -> str:
    pattern = re.compile(rf"{re.escape(diagram_type)}(?=\s|$)")
    matches = list(pattern.finditer(mermaid_code))
    if not matches:
        return mermaid_code.strip()
    if len(matches) == 1:
        return mermaid_code[matches[0].start():].strip()
    return mermaid_code[matches[0].start():matches[1].start()].strip()


def _normalize_mindmap_root(mermaid_code: str) -> str:
    lines = mermaid_code.splitlines()
    if not lines:
        return mermaid_code

    for idx in range(1, len(lines)):
        stripped = lines[idx].strip()
        if not stripped:
            continue

        indent = re.match(r"^\s*", lines[idx]).group(0) or "  "
        match = re.match(r"^root\s*\(\((.*)\)\)\s*$", stripped)
        if match:
            label = match.group(1).strip()
        else:
            label = stripped
        lines[idx] = f"{indent}root(({label}))"
        return "\n".join(lines).strip()

    return mermaid_code.strip()


def _normalize_mermaid_code(mermaid_code: str, diagram_type: str) -> str:
    normalized = _strip_markdown_fences(mermaid_code.strip())
    normalized = _extract_single_diagram_block(normalized, diagram_type)
    if diagram_type == "mindmap":
        normalized = _normalize_mindmap_root(normalized)
    return normalized.strip()


def _set_svg_root_background(svg_output: str, background_color: str) -> str:
    root_style_pattern = re.compile(r"(<svg\b[^>]*?)\sstyle=\"[^\"]*\"([^>]*>)", flags=re.IGNORECASE)
    if root_style_pattern.search(svg_output):
        return root_style_pattern.sub(
            rf'\1 style="background-color: {background_color};"\2',
            svg_output,
            count=1,
        )

    root_tag_pattern = re.compile(r"(<svg\b[^>]*)(>)", flags=re.IGNORECASE)
    return root_tag_pattern.sub(
        rf'\1 style="background-color: {background_color};"\2',
        svg_output,
        count=1,
    )


async def create_mermaid_diagram_scene(
    scene: Dict[str, Any],
    style: VideoStyle,
    llm: Optional[WorkflowLLMAdapter] = None,
) -> str:
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
    #caption_text = scene.get("text", "")
    caption_text = ""
    voice_over = scene.get("voice_over", "")
    voice_path = scene.get("voice_path", "")
    
    if not description:
        raise ValueError("Mermaid diagram scene requires 'description' field")
    
    if not voice_over:
        raise ValueError("Mermaid diagram scene requires 'voice_over' field")

    caption_html = render_markdown_html(caption_text) if caption_text else ""
    
    # Prefer the repo-managed Mermaid CLI wrapper over a global install.
    mermaid_cli = os.environ.get("MERMAID_CLI", DEFAULT_MERMAID_CLI)

    # Generate mermaid diagram code using LLM with retry logic for syntax errors
    svg_content = await generate_mermaid_image_with_retry(
        diagram_type,
        description,
        mermaid_cli,
        llm=llm,
    )
    
    
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
            padding: 0;
            font-size: var(--base-font-size);
            line-height: var(--line-height);
            overflow: hidden;
        }}
        
        .diagram-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 100%;
            position: relative;
            padding: var(--margin);
        }}
        
        .mermaid-svg {{
            width: 100%;
            height: 100%;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 0;
            box-shadow: none;
            background: white;
            padding: min(20px, var(--padding));
        }}
        
        .mermaid-svg svg {{
            width: 100%;
            height: 100%;
            max-width: 100%;
            max-height: 100%;
            object-fit: contain;
        }}
        
        .caption-container {{
            position: absolute;
            left: 0;
            right: 0;
            bottom: 0;
            padding: calc(var(--padding) * 0.75) var(--margin) var(--margin);
            text-align: center;
            background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.45) 100%);
        }}
        
        .caption-text {{
            font-size: var(--subtitle-size);
            font-weight: var(--title-weight);
            color: var(--primary-color);
            line-height: var(--line-height);
            word-wrap: break-word;
            font-family: var(--primary-font);
        }}

        .caption-text > :first-child {{
            margin-top: 0;
        }}

        .caption-text > :last-child {{
            margin-bottom: 0;
        }}

        .caption-text p,
        .caption-text li {{
            font-size: var(--subtitle-size);
        }}

        .caption-text ul,
        .caption-text ol {{
            display: inline-block;
            text-align: left;
            padding-left: 1.2em;
            margin: 0.4em auto;
        }}

        .caption-text strong {{
            color: var(--accent-color);
        }}
    </style>
</head>
<body>
    <div class="diagram-container">
        <div class="mermaid-svg">
{svg_content}
        </div>
    </div>
    {f'<div class="caption-container"><div class="caption-text">{caption_html}</div></div>' if caption_text else ''}
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
    # try:
    #     if os.path.exists(composite_image_path):
    #         os.remove(composite_image_path)
    #     if should_cleanup_audio and os.path.exists(audio_path):
    #         os.remove(audio_path)
    #     if os.path.exists(html_temp_path):
    #         os.remove(html_temp_path)
    # except:
    #     pass  # Ignore cleanup errors

    return video_path


async def generate_mermaid_image_with_retry(
    diagram_type: str,
    description: str,
    mermaid_cli: str,
    max_retries: int = 3,
    llm: Optional[WorkflowLLMAdapter] = None,
) -> str:
    """
    Generate Mermaid code and retry only when Mermaid CLI reports the code
    is invalid and can be repaired by the LLM.

    Args:
        diagram_type: Type of diagram (flowchart, sequenceDiagram, etc.)
        description: Description of what the diagram should show
        mermaid_cli: Path to mermaid CLI tool
        max_retries: Maximum number of Mermaid-repair attempts

    Returns:
        SVG content as string
    """
    
    llm = llm or WorkflowLLMAdapter()
    
    diagram_prompt = f"""
    Create a {diagram_type} diagram using Mermaid syntax for the following description:
    {description}
    
    Constraints:
    {_diagram_generation_constraints(diagram_type)}

    Make sure the diagram is valid {diagram_type} syntax.
    """
    
    messages = [HumanMessage(content=diagram_prompt)]

    for attempt in range(max_retries):
        try:
            # Generate mermaid code
            response = await llm.ainvoke(messages)
            mermaid_code = _normalize_mermaid_code(response.content, diagram_type)

            if not mermaid_code:
                raise Exception("Failed to generate mermaid diagram code")

            # Try to generate SVG - this will fail if there are syntax errors
            svg_content = await generate_svg_from_mermaid(mermaid_code, mermaid_cli)

            # If we get here, the mermaid code is valid
            return svg_content

        except MermaidRenderError as e:
            if attempt == max_retries - 1:
                raise Exception(
                    f"Failed to generate mermaid diagram after {max_retries} repair attempts: {str(e)}"
                ) from e

            messages.append(AIMessage(content=e.mermaid_code))
            messages.append(
                HumanMessage(
                    content=_build_mermaid_fix_prompt(diagram_type, e.mermaid_code, e.cli_error)
                )
            )
        except Exception as e:
            raise Exception(f"Failed to generate mermaid diagram: {str(e)}") from e

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
        cmd = [
            mermaid_cli,
            "-i",
            "-",
            "-e",
            "svg",
            "-o",
            "-",
            "-t",
            DEFAULT_MERMAID_THEME,
            "-b",
            DEFAULT_MERMAID_BACKGROUND,
        ]
        
        result = subprocess.run(
            cmd,
            input=mermaid_code,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            svg_output = result.stdout
            svg_output = _set_svg_root_background(svg_output, DEFAULT_MERMAID_BACKGROUND)
            return svg_output
        else:
            cli_error = (result.stderr or "Unknown Mermaid CLI error").strip()
            raise MermaidRenderError(
                f"Failed to generate SVG: {cli_error}",
                mermaid_code=mermaid_code,
                cli_error=cli_error,
            )
            
    except subprocess.TimeoutExpired:
        raise Exception("Timeout while generating SVG from mermaid code")
    except MermaidRenderError:
        raise
    except Exception as e:
        raise Exception(f"Error generating SVG: {str(e)}")
