"""Definition scene type module for video creation"""

import os
import markdown
from typing import Dict, Any
from ..VideoStyle import VideoStyle

# Import utility functions
from ..video_utils.html2image import capture_image
import subprocess
from .shared import get_or_create_voice_audio





async def create_definition_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """
    Create a definition scene video.

    Args:
        scene: Scene data containing:
            - term: string
            - definition: string - Definition in markdown style
            - voice_over: string
        style: Video style configuration

    Returns:
        Local file path to the generated video
    """

    # Extract scene data
    term = scene.get("term", "")
    definition = scene.get("definition", "")
    voice_over = scene.get("voice_over", "")
    voice_path = scene.get("voice_path", "")

    if not term:
        raise ValueError("Definition scene requires 'term' field")
    
    if not definition:
        raise ValueError("Definition scene requires 'definition' field")
    
    if not voice_over:
        raise ValueError("Definition scene requires 'voice_over' field")
    
    # Convert markdown definition to HTML
    try:
        definition_html = markdown.markdown(
            definition,
            extensions=['codehilite', 'fenced_code', 'tables', 'toc']
        )
    except Exception as e:
        # Fallback to plain text if markdown conversion fails
        definition_html = f"<p>{definition}</p>"
    
    # Create HTML content for definition display
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Definition Scene</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/dark.min.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.8/katex.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.8/katex.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/KaTeX/0.16.8/contrib/auto-render.min.js"></script>
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
        }}
        
        .definition-container {{
            width: 100%;
            display: flex;
            flex-direction: column;
            gap: var(--padding);
        }}
        
        .term-container {{
            text-align: center;
            padding: var(--inner-padding);
            margin-bottom: 0;
        }}
        
        .term-text {{
            font-size: var(--title-size);
            font-weight: var(--title-weight);
            color: var(--primary-color);
        }}
        
        .definition-content {{
            background: var(--card-bg);
            border: var(--border-width) solid var(--border-color);
            border-radius: var(--border-radius);
            padding: var(--padding);
            box-shadow: var(--box-shadow);
            line-height: var(--line-height);
            overflow-wrap: break-word;
            width: 100%;
        }}
        
        .definition-content p {{
            font-size: var(--body-size);
            font-weight: var(--body-weight);
            color: var(--primary-color);
            margin-bottom: var(--padding);
            word-wrap: break-word;
        }}
        
        .definition-content h1, .definition-content h2, .definition-content h3 {{
            color: var(--accent-color);
            margin-bottom: calc(var(--padding) / 2);
            margin-top: var(--padding);
        }}
        
        .definition-content ul, .definition-content ol {{
            padding-left: calc(var(--padding) * 1.5);
            margin-bottom: var(--padding);
        }}
        
        .definition-content li {{
            font-size: var(--body-size);
            color: var(--primary-color);
            margin-bottom: calc(var(--padding) / 4);
        }}
        
        .definition-content code {{
            background: transparent;
            color: var(--code-color);
            padding: 4px 8px;
            border-radius: var(--small-radius);
            font-family: var(--secondary-font);
            font-size: var(--code-size);
            border: var(--border-width) solid var(--code-border);
        }}
        
        .definition-content pre {{
            background: transparent;
            color: var(--code-color);
            padding: var(--padding);
            border-radius: var(--border-radius);
            overflow-x: auto;
            margin: var(--padding) 0;
            font-family: var(--secondary-font);
            font-size: var(--code-size);
            border: var(--border-width) solid var(--code-border);
        }}
        
        .definition-content pre code {{
            background: none;
            padding: 0;
            font-size: var(--code-size);
            border: none;
        }}
        
        .definition-content blockquote {{
            border-left: 4px solid var(--quote-border);
            padding-left: var(--padding);
            margin: var(--padding) 0;
            font-style: italic;
            color: var(--secondary-color);
        }}
        
        .definition-content table {{
            border-collapse: collapse;
            width: 100%;
            margin: var(--padding) 0;
        }}
        
        .definition-content th, .definition-content td {{
            border: var(--border-width) solid var(--table-border);
            padding: var(--inner-padding);
            text-align: left;
            font-size: var(--body-size);
        }}
        
        .definition-content th {{
            background: var(--table-header-bg);
            font-weight: var(--title-weight);
        }}
        
        /* KaTeX styling for math equations - Mobile optimized */
        .katex {{
            font-size: var(--body-size) !important;
            overflow-x: auto;
            overflow-y: hidden;
        }}
        
        .katex-display {{
            margin: var(--padding) 0 !important;
            text-align: center;
            overflow-x: auto;
        }}
        
        /* Override highlight.js colors for better mobile visibility */
        .hljs {{
            background: transparent !important;
            color: var(--code-color) !important;
            font-size: var(--code-size) !important;
        }}
        
        /* Mobile-specific improvements */
        @media (max-width: 1200px) {{
            .definition-content {{
                font-size: var(--body-size);
            }}
            
            .definition-content pre {{
                font-size: var(--code-size);
                overflow-x: scroll;
                -webkit-overflow-scrolling: touch;
            }}
            
            .katex {{
                font-size: calc(var(--body-size) * 0.9) !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="definition-container">
        <div class="term-container">
            <div class="term-text">{term}</div>
        </div>
        <div class="definition-content">
            {definition_html}
        </div>
    </div>
    
    <script>
        // Highlight code blocks
        hljs.highlightAll();
        
        // Render math equations
        renderMathInElement(document.body, {{
            delimiters: [
                {{left: "$$", right: "$$", display: true}},
                {{left: "$", right: "$", display: false}},
                {{left: "\\\\[", right: "\\\\]", display: true}},
                {{left: "\\\\(", right: "\\\\)", display: false}}
            ]
        }});
    </script>
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
        raise Exception("Failed to capture image for definition scene")
    
    audio_path, should_cleanup_audio = await get_or_create_voice_audio(
        voice_over,
        voice_path,
        style.voice_name,
    )
    
    if not audio_path:
        raise Exception("Failed to generate audio for definition scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    # Create video by combining image and audio using ffmpeg
    import uuid
    video_filename = f"definition_scene_{uuid.uuid4()}.mp4"
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
