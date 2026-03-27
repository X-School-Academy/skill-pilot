"""Quiz scene type module for video creation"""

import os
from typing import Dict, Any, List
from ..VideoStyle import VideoStyle

# Import utility functions
from ..video_utils.screen_recording import record_screen
import subprocess
from .shared import get_or_create_voice_audio


async def create_quiz_scene(scene: Dict[str, Any], style: VideoStyle) -> str:
    """
    Create a quiz scene video.

    Args:
        scene: Scene data containing:
            - question: string
            - options: list of strings (4 options)
            - answer: number - correct index (0-based)
            - question_voice_over: string - explain the question
            - answer_voice_over: string - explain the correct answer
        style: Video style configuration

    Returns:
        Local file path to the generated video
    """

    # Extract scene data
    question = scene.get("question", "")
    options = scene.get("options", [])
    correct_answer = scene.get("answer", 0)
    question_voice_over = scene.get("question_voice_over", "")
    answer_voice_over = scene.get("answer_voice_over", "")
    question_voice_path = scene.get("question_voice_path", "")
    answer_voice_path = scene.get("answer_voice_path", "")

    if not question:
        raise ValueError("Quiz scene requires 'question' field")
    
    if len(options) != 4:
        raise ValueError("Quiz scene requires exactly 4 options")
    
    if not question_voice_over:
        raise ValueError("Quiz scene requires 'question_voice_over' field")
    
    if not answer_voice_over:
        raise ValueError("Quiz scene requires 'answer_voice_over' field")
    
    if correct_answer < 0 or correct_answer >= len(options):
        raise ValueError("Quiz scene 'answer' index out of range")
    
    # Generate options HTML with letters A, B, C, D
    option_letters = ['A', 'B', 'C', 'D']
    options_html = ""
    for i, option in enumerate(options):
        is_correct = i == correct_answer
        options_html += f"""
        <div class="quiz-option" data-index="{i}" data-correct="{str(is_correct).lower()}">
            <div class="option-letter">{option_letters[i]}</div>
            <div class="option-text">{option}</div>
        </div>
        """
    
    # Generate or reuse audio files for both phases before building the timed animation.
    question_audio_path, should_cleanup_question_audio = await get_or_create_voice_audio(
        question_voice_over,
        question_voice_path,
        style.voice_name,
    )
    answer_audio_path, should_cleanup_answer_audio = await get_or_create_voice_audio(
        answer_voice_over,
        answer_voice_path,
        style.voice_name,
    )

    if not question_audio_path:
        raise Exception("Failed to generate question audio for quiz scene")

    # Upload audio files to S3 and add URLs to scene data
    scene['question_voice_url'] = question_audio_path
    scene['answer_voice_url'] = answer_audio_path

    if not answer_audio_path:
        raise Exception("Failed to generate answer audio for quiz scene")
    
    # Get individual audio durations
    question_duration = await get_audio_duration(question_audio_path)
    answer_duration = await get_audio_duration(answer_audio_path)
    total_duration = question_duration + answer_duration

    # Create HTML content for quiz (after getting audio durations)
    css_vars = style.to_css_vars()
    css_vars_str = "\n".join([f"    {key}: {value};" for key, value in css_vars.items()])
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quiz Scene</title>
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
        }}
        
        .quiz-container {{
            width: 90%;
            max-width: 1200px;  /* Increased for better landscape support */
            display: flex;
            flex-direction: column;
            gap: var(--padding);
        }}
        
        .question-container {{
            border-radius: var(--border-radius);
            padding: var(--padding);
            text-align: left;
            margin-bottom: calc(var(--padding) * 2);
        }}
        
        .question-text {{
            font-size: var(--title-size);
            font-weight: var(--title-weight);
            color: var(--primary-color);
            line-height: var(--line-height);
            word-wrap: break-word;
        }}
        
        .options-container {{
            display: grid;
            grid-template-columns: 1fr;  /* Portrait: single column */
            gap: var(--padding);
        }}
        
        /* Landscape layout: use 2 columns for better space utilization */
        @media (min-aspect-ratio: 16/10) {{
            .options-container {{
                grid-template-columns: 1fr 1fr;  /* Landscape: two columns */
                gap: calc(var(--padding) * 1.5);
            }}
        }}
        
        .quiz-option {{
            display: flex;
            align-items: center;
            background: rgba(255, 255, 255, 0.05);
            border: var(--border-width) solid var(--border-color);
            border-radius: var(--border-radius);
            padding: var(--padding);
            cursor: pointer;
            transition: all var(--animation-duration) var(--animation-easing);
        }}
        
        .quiz-option:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--accent-color);
        }}
        
        .quiz-option.correct {{
            background: var(--success-color) !important;
            border-color: var(--success-color) !important;
            color: white !important;
            transform: scale(1.02);
            box-shadow: 0 4px 20px rgba(48, 209, 88, 0.3);
        }}
        
        .option-letter {{
            width: 40px;
            height: 40px;
            background: var(--accent-color);
            color: white;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: var(--body-size);
            font-weight: var(--title-weight);
            margin-right: var(--padding);
            flex-shrink: 0;
        }}
        
        .option-text {{
            font-size: var(--body-size);
            font-weight: var(--body-weight);
            line-height: var(--line-height);
            word-wrap: break-word;
            flex: 1;
        }}
        
        .quiz-option.correct .option-letter {{
            background: white;
            color: var(--success-color);
        }}
    </style>
</head>
<body>
    <div class="quiz-container">
        <div class="question-container">
            <div class="question-text">{question}</div>
        </div>
        <div class="options-container">
            {options_html}
        </div>
    </div>
    
    <script>
        let questionPhase = true;
        let videoStarted = false;
        let videoEnded = false;
        
        // Audio durations from server (in milliseconds)
        const questionDuration = {question_duration * 1000};  // Convert to milliseconds
        const answerDuration = {answer_duration * 1000};      // Convert to milliseconds
        
        function video_started() {{
            videoStarted = true;
            return true;
        }}
        
        function video_ended() {{
            return videoEnded;
        }}
        
        // Show answer after question audio duration
        setTimeout(() => {{
            questionPhase = false;
            showAnswers();
            // End video after answer audio duration
            setTimeout(() => {{
                videoEnded = true;
            }}, answerDuration);
        }}, questionDuration);
        
        function showAnswers() {{
            console.log('showAnswers called');
            const options = document.querySelectorAll('.quiz-option');
            console.log('Found options:', options.length);
            
            options.forEach((option, index) => {{
                const isCorrect = option.getAttribute('data-correct') === 'true';
                console.log(`Option ${{index}}: isCorrect=${{isCorrect}}`);
                
                if (isCorrect) {{
                    console.log(`Adding correct class to option ${{index}}`);
                    option.classList.add('correct');
                    
                    // Update the letter as well
                    const letterElement = option.querySelector('.option-letter');
                    if (letterElement) {{
                        letterElement.style.backgroundColor = 'white';
                        letterElement.style.color = '#30D158';
                    }}
                    
                    console.log(`Applied styles to option ${{index}}`);
                }}
            }});
        }}
    </script>
</body>
</html>
"""
    
    # Combine audio files
    import uuid
    combined_audio_filename = f"quiz_combined_audio_{uuid.uuid4()}.mp3"
    combined_audio_path = f"/tmp/{combined_audio_filename}"
    
    # Use ffmpeg to concatenate audio files
    ffmpeg_audio_cmd = [
        "ffmpeg", "-y",
        "-i", question_audio_path,
        "-i", answer_audio_path,
        "-filter_complex", "[0:0][1:0]concat=n=2:v=0:a=1[out]",
        "-map", "[out]",
        combined_audio_path
    ]
    
    try:
        result = subprocess.run(ffmpeg_audio_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise Exception(f"FFmpeg audio concatenation failed: {result.stderr}")
    except Exception as e:
        raise Exception(f"Failed to combine audio files: {str(e)}")
    
    # Create video using screen recording
    video_filename = f"/tmp/quiz_scene_{uuid.uuid4()}.mp4"
    
    try:
        is_horizontal = style.width > style.height
        video_path = await record_screen(
            html_code=html_content,
            output_file=video_filename,
            duration=total_duration,
            isHorizontal=is_horizontal,
            view_width=style.width,
            view_height=style.height,
            audio_file=combined_audio_path
        )
        
        if not video_path:
            raise Exception("Failed to record quiz scene")
        
    except Exception as e:
        raise Exception(f"Failed to create quiz video: {str(e)}")
    
    # Return the temporary video file path (don't upload to S3 here)
    if not os.path.exists(video_path):
        raise Exception("Video file was not created successfully")
    
    # Clean up temporary files (keep the video file)
    try:
        if should_cleanup_question_audio and os.path.exists(question_audio_path):
            os.remove(question_audio_path)
        if should_cleanup_answer_audio and os.path.exists(answer_audio_path):
            os.remove(answer_audio_path)
        if os.path.exists(combined_audio_path):
            os.remove(combined_audio_path)
    except:
        pass  # Ignore cleanup errors

    return video_path


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
