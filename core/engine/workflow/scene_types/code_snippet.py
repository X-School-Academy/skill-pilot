"""Code Snippet scene type module for video creation"""

import os
from typing import Dict, Any
from ..VideoStyle import VideoStyle

# Import utility functions

from llm import LLM
from ..video_utils.html2image import capture_image
import subprocess
from tts_service import async_text_to_audio_file

async def create_code_snippet_scene(scene: Dict[str, Any], style: VideoStyle, cost_member_id: int = None) -> tuple[str, float]:
    """
    Create a code snippet scene video.

    Args:
        scene: Scene data containing:
            - code: string - Markdown code block enclosed by three backticks
            - voice_over: string
        style: Video style configuration
        cost_member_id: Member ID for cost tracking (None for system cost)

    Returns:
        tuple: (video_path, scene_cost) - Local file path to the generated video and accumulated cost for this scene
    """

    # Extract scene data
    code = scene.get("code", "")
    voice_over = scene.get("voice_over", "")

    # Track accumulated cost for this scene
    scene_cost = 0.0
    
    if not code:
        raise ValueError("Code snippet scene requires 'code' field")
    
    if not voice_over:
        raise ValueError("Code snippet scene requires 'voice_over' field")
    
    # Parse code block to extract language and code content
    code_lines = code.strip().split('\n')
    if code_lines[0].startswith('```'):
        language = code_lines[0][3:].strip() or 'text'
        code_content = '\n'.join(code_lines[1:-1]) if len(code_lines) > 2 else ''
    else:
        language = 'text'
        code_content = code
    
    # Escape HTML characters in code
    import html
    escaped_code = html.escape(code_content)
    
    # Create HTML content with syntax highlighted code
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mobile-Optimized Code Snippet Scene</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/styles/dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.8.0/highlight.min.js"></script>
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
            position: relative;
            overflow: hidden;
        }}
        
        /* Animated background elements */
        body::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: 
                radial-gradient(circle at 20% 30%, rgba(0, 122, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 70%, rgba(48, 209, 88, 0.08) 0%, transparent 50%);
        }}
        
        .scene-container {{
            width: 100%;
            max-width: 95%;
            position: relative;
            z-index: 1;
        }}
        
        .code-container {{
            background: var(--code-bg);
            border-radius: var(--border-radius);
            padding: 0;
            border: var(--border-width) solid var(--code-border);
            box-shadow: var(--box-shadow), var(--glow-shadow);
            overflow: hidden;
            backdrop-filter: blur(10px);
        }}
        
        .code-header {{
            background: var(--header-bg);
            padding: var(--inner-padding);
            border-bottom: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
            backdrop-filter: blur(10px);
        }}
        
        .language-tag {{
            background: linear-gradient(135deg, var(--accent-color), #0056D6);
            color: white;
            padding: 8px 16px;
            border-radius: var(--small-radius);
            font-size: var(--caption-size);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            box-shadow: 0 2px 8px rgba(0, 122, 255, 0.3);
        }}
        
        .window-controls {{
            display: flex;
            gap: 8px;
        }}
        
        .control-dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
            opacity: 0.7;
        }}
        
        .control-dot.close {{ background: var(--error-color); }}
        .control-dot.minimize {{ background: var(--warning-color); }}
        .control-dot.maximize {{ background: var(--success-color); }}
        
        .code-content {{
            padding: var(--padding);
            font-family: var(--code-font);
            font-size: var(--code-size);
            line-height: var(--line-height);
            overflow-x: auto;
            max-height: 70vh;
            position: relative;
        }}
        
        .code-content pre {{
            margin: 0;
            white-space: pre-wrap;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }}
        
        .code-content code {{
            font-family: inherit;
            font-size: inherit;
            background: none !important;
            padding: 0 !important;
        }}
        
        /* Enhanced syntax highlighting for mobile */
        .hljs {{
            background: transparent !important;
            color: #e5e5e5 !important;
            font-weight: 400;
        }}
        
        .hljs-keyword {{ color: #FF7A93 !important; font-weight: 600; }}
        .hljs-string {{ color: #A8FF60 !important; }}
        .hljs-number {{ color: #96CBFE !important; }}
        .hljs-comment {{ color: #7C7C7C !important; font-style: italic; }}
        .hljs-function {{ color: #FFD700 !important; font-weight: 600; }}
        .hljs-variable {{ color: #C6C5FE !important; }}
        .hljs-operator {{ color: #EDEDED !important; font-weight: 600; }}
        .hljs-title {{ color: #96CBFE !important; font-weight: bold; }}
        
        /* Scrollbar styling for mobile */
        .code-content::-webkit-scrollbar {{
            width: 8px;
            height: 8px;
        }}
        
        .code-content::-webkit-scrollbar-track {{
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }}
        
        .code-content::-webkit-scrollbar-thumb {{
            background: var(--accent-color);
            border-radius: 4px;
        }}
        
        .code-content::-webkit-scrollbar-thumb:hover {{
            background: #0056D6;
        }}
        
        /* Responsive adjustments */
        @media (max-width: 1080px) {{
            :root {{
                --margin: 32px;
                --padding: 24px;
                --inner-padding: 20px;
                --code-size: 24px;
            }}
        }}
        
        @media (max-width: 768px) {{
            :root {{
                --margin: 24px;
                --padding: 20px;
                --inner-padding: 16px;
                --code-size: 22px;
                --border-radius: 12px;
            }}
        }}
    </style>
</head>
<body>
    <div class="scene-container">
        <div class="code-container">
            <div class="code-header">
                <div class="language-tag">{language.upper()}</div>
                <div class="window-controls">
                    <div class="control-dot close"></div>
                    <div class="control-dot minimize"></div>
                    <div class="control-dot maximize"></div>
                </div>
            </div>
            <div class="code-content">
                <pre><code class="language-{language}">{escaped_code}</code></pre>
            </div>
        </div>
    </div>
    
    <script>
        // Initialize syntax highlighting
        hljs.highlightAll();
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
        raise Exception("Failed to capture image for code snippet scene")
    
    # Generate audio file using Gemini TTS or fallback to LLM
    tts_cost = 0.0
    try:
        audio_path, tts_cost = await async_text_to_audio_file(
            voice_over,
            voice=style.voice_name,
            format="wav",
            cost_member_id=cost_member_id,
            cost_note="Code snippet scene - voice narration"
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        # Fallback to original LLM method
        async with LLM() as llm:
            audio_path, tts_cost = await llm.text_to_audio_file(
                voice_over, 
                voice=style.voice_name,
                cost_member_id=cost_member_id,
                cost_note="Code snippet scene - voice narration (fallback MS TTS)"
            )
    
    if not audio_path:
        raise Exception("Failed to generate audio for code snippet scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    scene_cost += tts_cost
    
    # Create video by combining image and audio using ffmpeg
    import uuid
    video_filename = f"code_snippet_scene_{uuid.uuid4()}.mp4"
    video_path = f"/tmp/{video_filename}"
    
    # Use ffmpeg to create video from image and audio with mobile optimization
    ffmpeg_cmd = [
        "ffmpeg", "-y",  # -y to overwrite output file
        "-loop", "1",  # Loop the image
        "-i", image_path,  # Input image
        "-i", audio_path,  # Input audio
        "-c:v", "libx264",  # Video codec
        "-crf", "18",
        "-c:a", "aac",  # PCM audio codec (no priming samples)
        "-pix_fmt", "yuv420p",  # Pixel format for compatibility
        "-profile:v", "baseline",  # Better mobile compatibility
        "-level", "3.0",  # Mobile-optimized level
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
