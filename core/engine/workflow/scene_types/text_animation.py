"""Text Animation scene type module for video creation"""

import os
from typing import Dict, Any
from ..VideoStyle import VideoStyle

# Import utility functions
from llm import LLM    
from ..video_utils.screen_recording import record_screen
import subprocess
from tts_service import async_text_to_audio_file

async def create_text_animation_scene(scene: Dict[str, Any], style: VideoStyle, cost_member_id: int = None) -> tuple[str, float]:
    """
    Create a text animation scene video.

    Args:
        scene: Scene data containing:
            - animation_type: string - 'fade-in', 'slide-in', 'typewriter', 'blink' or 'scale-up'
            - text: string - the text for animation
            - voice_over: string
        style: Video style configuration
        cost_member_id: Member ID for cost tracking (None for system cost)

    Returns:
        tuple: (video_path, scene_cost) - Local file path to the generated video and accumulated cost for this scene
    """

    # Extract scene data
    animation_type = scene.get("animation_type", "fade-in")
    text = scene.get("text", "")
    voice_over = scene.get("voice_over", "")

    # Track accumulated cost for this scene
    scene_cost = 0.0
    
    if not text:
        raise ValueError("Text animation scene requires 'text' field")
    
    if not voice_over:
        raise ValueError("Text animation scene requires 'voice_over' field")
    
    supported_animations = ['fade-in', 'slide-in', 'typewriter', 'blink', 'scale-up']
    if animation_type not in supported_animations:
        raise ValueError(f"Unsupported animation type: {animation_type}. Supported: {supported_animations}")
    
    # Create animation CSS based on type
    animation_css = ""
    animation_duration = "3s"
    
    if animation_type == "fade-in":
        animation_css = """
        @keyframes fadeIn {
            0% { opacity: 0; }
            100% { opacity: 1; }
        }
        .animated-text {
            animation: fadeIn 3s ease-in-out;
        }
        """
    elif animation_type == "slide-in":
        animation_css = """
        @keyframes slideIn {
            0% { transform: translateX(-100%); opacity: 0; }
            100% { transform: translateX(0); opacity: 1; }
        }
        .animated-text {
            animation: slideIn 3s ease-out;
        }
        """
    elif animation_type == "typewriter":
        # Calculate character count for typewriter effect
        char_count = len(text)
        animation_css = f"""
        @keyframes typewriter {{
            0% {{ width: 0; }}
            100% {{ width: 100%; }}
        }}
        @keyframes blinkCursor {{
            0%, 50% {{ border-right-color: var(--accent-color); }}
            51%, 100% {{ border-right-color: transparent; }}
        }}
        .animated-text {{
            overflow: hidden;
            white-space: nowrap;
            border-right: 3px solid var(--accent-color);
            width: 0;
            animation: typewriter 4s steps({char_count}, end), blinkCursor 0.75s step-end infinite;
        }}
        """
        animation_duration = "5s"
    elif animation_type == "blink":
        animation_css = """
        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0.3; }
        }
        .animated-text {
            animation: blink 1s ease-in-out infinite;
        }
        """
    elif animation_type == "scale-up":
        animation_css = """
        @keyframes scaleUp {
            0% { transform: scale(0.5); opacity: 0; }
            50% { transform: scale(1.1); opacity: 0.8; }
            100% { transform: scale(1); opacity: 1; }
        }
        .animated-text {
            animation: scaleUp 2s ease-out;
        }
        """
    
    # Generate audio file using Gemini TTS or fallback to LLM
    tts_cost = 0.0
    try:
        audio_path, tts_cost = await async_text_to_audio_file(
            voice_over,
            voice=style.voice_name,
            format="wav",
            cost_member_id=cost_member_id,
            cost_note="Text animation scene - voice narration"
        )
    except Exception as e:
        print(f"Gemini TTS failed, falling back to LLM: {e}")
        # Fallback to original LLM method
        async with LLM() as llm:
            audio_path, tts_cost = await llm.text_to_audio_file(
                voice_over, 
                voice=style.voice_name,
                cost_member_id=cost_member_id,
                cost_note="Text animation scene - voice narration (fallback MS TTS)"
            )
    
    if not audio_path:
        raise Exception("Failed to generate audio for text animation scene")
    
    # Upload audio to S3 and add URL to scene data
    scene['voice_url'] = audio_path

    scene_cost += tts_cost
    
    # Get audio duration to determine video length
    audio_duration = await get_audio_duration(audio_path)
    total_duration = max(audio_duration, int(animation_duration.replace('s', '')) + 1)
    
    # Create HTML content with animated text
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Text Animation Scene</title>
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
            overflow: hidden;
        }}
        
        .text-container {{
            max-width: 90%;
            text-align: center;
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        
        .animated-text {{
            font-size: var(--title-size);
            font-weight: var(--title-weight);
            color: var(--primary-color);
            line-height: var(--line-height);
            word-wrap: break-word;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }}
        
        {animation_css}
        
        /* Special styling for typewriter effect */
        .typewriter-container {{
            display: inline-block;
            max-width: 100%;
        }}
        
        /* Background gradient for more visual interest */
        body::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(ellipse at center, rgba(59, 130, 246, 0.1) 0%, transparent 70%);
            pointer-events: none;
        }}
    </style>
</head>
<body>
    <div class="text-container">
        <div class="animated-text{' typewriter-container' if animation_type == 'typewriter' else ''}">{text}</div>
    </div>
    
    <script>
        let animationStarted = false;
        let videoStarted = false;
        let videoEnded = false;
        
        function video_started() {{
            if (!animationStarted) {{
                animationStarted = true;
                videoStarted = true;
                // End video after total duration (audio + buffer)
                setTimeout(() => {{
                    videoEnded = true;
                }}, {total_duration * 1000});
            }}
            return videoStarted;
        }}
        
        function video_ended() {{
            return videoEnded;
        }}
        
        // Trigger animation start
        setTimeout(() => {{
            document.querySelector('.animated-text').style.visibility = 'visible';
        }}, 100);
    </script>
</body>
</html>
"""
    
    # Create video using screen recording
    import uuid
    video_filename = f"/tmp/text_animation_scene_{uuid.uuid4()}.mp4"
    
    try:
        is_horizontal = style.width > style.height
        video_path = await record_screen(
            html_code=html_content,
            output_file=video_filename,
            duration=total_duration,
            isHorizontal=is_horizontal,
            view_width=style.width,
            view_height=style.height,
            audio_file=audio_path
        )
        
        if not video_path:
            raise Exception("Failed to record text animation scene")
        
    except Exception as e:
        raise Exception(f"Failed to create text animation video: {str(e)}")
    
    # Return the temporary video file path (don't upload to S3 here)
    if not os.path.exists(video_path):
        raise Exception("Video file was not created successfully")
    
    # Clean up temporary files (keep the video file)
    try:
        if os.path.exists(audio_path):
            os.remove(audio_path)
        if os.path.exists(f"/tmp/{video_filename}"):
            os.remove(f"/tmp/{video_filename}")
    except:
        pass  # Ignore cleanup errors

    return video_path, scene_cost


async def get_audio_duration(audio_path: str) -> float:
    """Get duration of audio file in seconds using ffprobe"""
    try:
        result = subprocess.run([
            "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
            "-of", "csv=p=0", audio_path
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return float(result.stdout.strip())
        else:
            return 10.0  # Default duration
    except:
        return 10.0  # Default duration if ffprobe fails
