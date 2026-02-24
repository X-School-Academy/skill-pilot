import os
import shutil
import time
import asyncio
import aiofiles
import base64
import uuid
from playwright.async_api import async_playwright
import argparse

# https://playwright.dev/python/

async def record_screen(
    html_code=None,
    url=None, 
    output_file=None, 
    duration=10.0, 
    video_framerate=30,
    isHorizontal=False,
    audio_file=None
):
    """Record the screen from a webpage rendered in a headless browser.

    Args:
        html_code (str, optional): The HTML content to render in the page (if no URL is provided).
        url (str, optional): The URL to load (if no HTML code is provided).
        output_file (str, optional): The path to the output MP4 file.
        duration (float, optional): Max time (in seconds) to wait for the #phaseDisplay element to hide.
        video_framerate (int, optional): The final output framerate for the MP4.
        isHorizontal (bool, optional): Whether to record in 1920x1080 (True) or 1080x1920 (False).
        audio_file (str, optional): Path to an audio file to be muxed with the video.
    """
    width, height = (1920, 1080) if isHorizontal else (1080, 1920)
    
    # Determine the output filename if not provided
    if output_file is None:
        output_file = f"/tmp/{uuid.uuid4()}.mp4"
    
    # Directory to store raw frames
    frames_dir = f"{output_file.replace('.mp4', '')}_frames"
    os.makedirs(frames_dir, exist_ok=True)
    
    if html_code:
        html_file = os.path.join(frames_dir, f'video_script_{str(uuid.uuid4())}.html')
        async with aiofiles.open(html_file, 'w') as f:
            await f.write(html_code)
            print(f"html_file: {html_file}")
        url = f'file://{os.path.abspath(html_file)}'
    
    # Launch browser
    print("Launching headless browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=True, args=['--no-sandbox'])
    #browser = await launch(headless=True, args=[
    #    '--no-sandbox',           # Security restriction bypass
    #    '--disable-dev-shm-usage' # /dev/shm is a shared memory filesystem
    #], executable_path='/home/frankhe/Dropbox/github_workspace/jit-app-service/bin/pw-linux-browsers/chromium_headless_shell-1179/chrome-linux/headless_shell')
    print("Browser launched.")
    context = await browser.new_context(
        viewport={'width': width, 'height': height},
        record_video_dir=frames_dir,
        record_video_size={'width': width, 'height': height}
    )
    page = await context.new_page()
    print("Page created.")
    
    if url:
        print(f"Loading URL: {url}")
        await page.goto(url)
    elif html_code:
        await page.set_content(html_code)
    else:
        raise ValueError("You must provide either `html_code` or `url`.")
    
    print(f"Recording screen for {duration} seconds...")
    # Wait until '#phaseDisplay' is visible (i.e. "recording" phase starts)
    # Not work on mac
    # await page.waitForSelector('#phaseDisplay', {'hidden': False})
    await page.wait_for_function('video_started()', polling=10, timeout=10 * 1000)
    print("Recording started.")

    # Wait until video ends or timeout
    try:
        await page.wait_for_function('video_ended()', polling=10, timeout=duration * 1.5 * 1000)
    except Exception as e:
        print(f"Error: {str(e)}")
        print(f"Timeout reached. Stopping recording.")
    await context.close()
    await browser.close()
    await playwright.stop()
    
    # Get the recorded video file
    video_files = [f for f in os.listdir(frames_dir) if f.endswith('.webm')]
    if not video_files:
        raise Exception(f"No video was recorded. Check the page and the duration: {duration} parameter.")
    
    recorded_video = os.path.join(frames_dir, video_files[0])
    
    # Convert to MP4 if needed
    command = ['ffmpeg', '-y', '-i', recorded_video]
    
    # Add audio input if an audio file is provided
    if audio_file is not None:
        command.extend(['-i', audio_file, '-c:a', 'aac', '-b:a', '192k'])
    else:
        command.extend(['-an'])  # No audio
    
    # Video settings
    command.extend([
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        output_file
    ])

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        
        stdout_decoded = stdout.decode().strip()
        stderr_decoded = stderr.decode().strip()
        
        if stdout_decoded:
            print("FFmpeg Output:", stdout_decoded)
        if stderr_decoded:
            print("FFmpeg Errors:", stderr_decoded)
        
        if process.returncode != 0:
            print(" ".join(command))
            raise Exception(f"FFmpeg failed with return code {process.returncode}: {stderr_decoded}")
        
    except FileNotFoundError:
        raise Exception("FFmpeg is not installed or not found in the system PATH.")
    except Exception as e:
        raise Exception(f"An error occurred while creating the video: {str(e)}")

    print(f"Done. Video is at {output_file}.")
    
    # Clean up frames directory
    shutil.rmtree(frames_dir)
    
    #return output_file
    print(f"RESULT_FILE={output_file}", flush=True)

def parse_args():
    parser = argparse.ArgumentParser(description="Screen recording script.")
    parser.add_argument("--html_code", default=None, help="HTML code to render inline.")
    parser.add_argument("--url", default=None, help="URL/path to load in the browser.")
    parser.add_argument("--output_file", default=None, help="Path to the video file.")
    parser.add_argument("--duration", type=float, default=10.0, help="Recording duration in seconds.")
    parser.add_argument("--video_framerate", type=int, default=30, help="Framerate of the recorded video.")
    parser.add_argument("--isHorizontal", action="store_true", help="Flag to record in horizontal mode.")
    parser.add_argument("--audio_file", default=None, help="Optional audio file to merge.")

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_args()

    asyncio.run(
        record_screen(
            html_code=args.html_code,
            url=args.url,
            output_file=args.output_file,
            duration=args.duration,
            video_framerate=args.video_framerate,
            isHorizontal=args.isHorizontal,
            audio_file=args.audio_file,
        )
    )
