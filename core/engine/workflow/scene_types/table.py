"""Table scene type module for video creation"""

import os
from typing import Dict, Any, List
from ..VideoStyle import VideoStyle

# Import utility functions
from llm import LLM    
from ..video_utils.html2image import capture_image
import subprocess
from tts_service import async_text_to_audio_file





async def create_table_scene(scene: Dict[str, Any], style: VideoStyle, cost_member_id: int = None) -> tuple[str, float]:
    """
    Create a table scene video.

    Args:
        scene: Scene data containing:
            - rows: list of lists of strings - table data including headers
            - text: string - caption of the table
            - voice_over: string
        style: Video style configuration
        cost_member_id: Member ID for cost tracking (None for system cost)

    Returns:
        tuple: (video_path, scene_cost) - Local file path to the generated video and accumulated cost for this scene
    """

    # Extract scene data
    rows = scene.get("rows", [])
    caption_text = scene.get("text", "")
    voice_over = scene.get("voice_over", "")

    # Track accumulated cost for this scene
    scene_cost = 0.0
    
    if not rows:
        raise ValueError("Table scene requires 'rows' field")
    
    if not voice_over:
        raise ValueError("Table scene requires 'voice_over' field")
    
    # Generate HTML table rows
    table_html = ""
    
    # First row as header if there are multiple rows
    if len(rows) > 1:
        header_row = rows[0]
        table_html += "<thead><tr>"
        for cell in header_row:
            table_html += f"<th>{cell}</th>"
        table_html += "</tr></thead>"
        
        # Remaining rows as body
        table_html += "<tbody>"
        for row in rows[1:]:
            table_html += "<tr>"
            for cell in row:
                table_html += f"<td>{cell}</td>"
            table_html += "</tr>"
        table_html += "</tbody>"
    else:
        # Single row as body
        table_html += "<tbody>"
        for row in rows:
            table_html += "<tr>"
            for cell in row:
                table_html += f"<td>{cell}</td>"
            table_html += "</tr>"
        table_html += "</tbody>"
    
    # Create HTML content with table
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Table Scene</title>
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
        
        .table-container {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            overflow-x: auto;
            overflow-y: auto;
            margin-bottom: 0;
            /* Mobile-friendly scrolling */
            -webkit-overflow-scrolling: touch;
        }}
        
        .data-table {{
            border-collapse: collapse;
            background: var(--card-bg);
            border-radius: var(--border-radius);
            overflow: hidden;
            max-width: 90%;
            box-shadow: var(--box-shadow);
        }}
        
        .data-table th {{
            background: var(--table-header-bg);
            color: var(--primary-color);
            font-size: var(--body-size);
            font-weight: var(--title-weight);
            padding: var(--padding);
            text-align: left;
            border: var(--border-width) solid var(--table-border);
        }}
        
        .data-table td {{
            font-size: var(--body-size);
            font-weight: var(--body-weight);
            color: var(--primary-color);
            padding: var(--padding);
            text-align: left;
            border: var(--border-width) solid var(--table-border);
            word-wrap: break-word;
        }}
        
        .data-table tr:nth-child(even) {{
            background: rgba(255, 255, 255, 0.05);
        }}
        
        /* Updated caption styling to match image_with_caption */
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
        
        /* Mobile-optimized scrollbar styling */
        .table-container::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        .table-container::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }}
        
        .table-container::-webkit-scrollbar-thumb {{
            background: rgba(255, 255, 255, 0.3);
            border-radius: 4px;
        }}
        
        .table-container::-webkit-scrollbar-thumb:hover {{
            background: rgba(255, 255, 255, 0.5);
        }}
    </style>
</head>
<body>
    <div class="table-container">
        <table class="data-table">
            {table_html}
        </table>
    </div>
    {f'<div class="caption-container"><div class="caption-text">{caption_text}</div></div>' if caption_text else ''}
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
        raise Exception("Failed to capture image for table scene")
    
    # Generate audio file using Gemini TTS or fallback to LLM
    tts_cost = 0.0
    try:
        audio_path, tts_cost = await async_text_to_audio_file(
            voice_over,
            voice=style.voice_name,
            format="wav",
            cost_member_id=cost_member_id,
            cost_note="Table scene - voice narration"
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        # Fallback to original LLM method
        async with LLM() as llm:
            audio_path, tts_cost = await llm.text_to_audio_file(
                voice_over, 
                voice=style.voice_name,
                cost_member_id=cost_member_id,
                cost_note="Table scene - voice narration (fallback MS TTS)"
            )
    
    if not audio_path:
        raise Exception("Failed to generate audio for table scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    scene_cost += tts_cost
    
    # Create video by combining image and audio using ffmpeg
    import uuid
    video_filename = f"table_scene_{uuid.uuid4()}.mp4"
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
