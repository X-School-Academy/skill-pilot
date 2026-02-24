import os
import shutil
import time
import asyncio
import aiofiles
import base64
import uuid
from playwright.async_api import async_playwright
import argparse
from logger import get_logger

# https://playwright.dev/python/

async def record_screen(
    html_code=None,
    url=None,
    output_file=None,
    duration=10.0,
    video_framerate=30,  # kept for backward compatibility
    isHorizontal=False,
    view_width=None,
    view_height=None,
    audio_file=None
):
    """Record the screen from a webpage rendered in a headless browser."""
    width, height = (1920, 1080) if isHorizontal else (1080, 1920)

    if view_width is not None and view_height is not None:
        width = view_width
        height = view_height

    if output_file is None:
        output_file = f"/tmp/{uuid.uuid4()}.mp4"

    frames_dir = f"{output_file.replace('.mp4', '')}_frames"
    os.makedirs(frames_dir, exist_ok=True)
    browser = None
    context = None
    playwright = None
    js_errors = []
    console_errors = []

    logger = get_logger("workflow.video_utils.screen_recording")

    if html_code:
        html_file = os.path.join(frames_dir, f"video_script_{str(uuid.uuid4())}.html")
        async with aiofiles.open(html_file, "w") as f:
            await f.write(html_code)
            logger.info("html_file: %s", html_file)
        url = f"file://{os.path.abspath(html_file)}"

    try:
        logger.info("Launching headless browser...")
        playwright = await async_playwright().start()
        if os.getenv("PYTHON_ENV") == "azure_container":
            browser = await playwright.chromium.launch(
                executable_path=os.getenv("PUPPETEER_EXECUTABLE_PATH"),
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )
        else:
            browser = await playwright.chromium.launch(headless=True, args=["--no-sandbox"])
        logger.info("Browser launched.")
        context = await browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=frames_dir,
            record_video_size={"width": width, "height": height},
        )
        page = await context.new_page()
        logger.info("Page created.")
        page.on("pageerror", lambda exc: js_errors.append(str(exc)))
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        if url:
            logger.info("Loading URL: %s", url)
            await page.goto(url)
        elif html_code:
            await page.set_content(html_code)
        else:
            raise ValueError("You must provide either `html_code` or `url`.")

        logger.info("Recording screen for %.2f seconds...", duration)
        await page.wait_for_function("video_started()", polling=10, timeout=10 * 1000)
        logger.info("Recording started.")

        try:
            await page.wait_for_function("video_ended()", polling=10, timeout=duration * 1.5 * 1000)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Error: %s", str(e))
            logger.warning("Timeout reached. Stopping recording.")

        if js_errors or console_errors:
            errors = []
            if js_errors:
                errors.append(f"page errors: {' | '.join(js_errors)}")
            if console_errors:
                errors.append(f"console errors: {' | '.join(console_errors)}")
            raise RuntimeError(f"JavaScript errors while recording: {'; '.join(errors)}")
    finally:
        if context is not None:
            await context.close()
        if browser is not None:
            await browser.close()
        if playwright is not None:
            await playwright.stop()

    video_files = [f for f in os.listdir(frames_dir) if f.endswith(".webm")]
    if not video_files:
        raise Exception(f"No video was recorded. Check the page and the duration: {duration} parameter.")

    recorded_video = os.path.join(frames_dir, video_files[0])

    command = ["ffmpeg", "-y", "-i", recorded_video]
    if audio_file is not None:
        command.extend(["-i", audio_file, "-c:a", "aac"])
    else:
        command.extend(["-an"])
    command.extend(
        [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            output_file,
        ]
    )

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        ffmpeg_timeout = max(15.0, duration + 5.0)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=ffmpeg_timeout)
        except asyncio.TimeoutError as exc:
            process.kill()
            await process.wait()
            raise TimeoutError(f"FFmpeg did not finish within {ffmpeg_timeout} seconds for {recorded_video}") from exc
        except asyncio.CancelledError:
            process.kill()
            await process.wait()
            raise

        stdout_decoded = stdout.decode().strip()
        stderr_decoded = stderr.decode().strip()

        if stdout_decoded:
            logger.debug("FFmpeg Output: %s", stdout_decoded)
        if stderr_decoded:
            logger.info("FFmpeg Errors: %s", stderr_decoded)

        if process.returncode != 0:
            logger.error("FFmpeg command failed: %s", " ".join(command))
            raise Exception(f"FFmpeg failed with return code {process.returncode}: {stderr_decoded}")

    except FileNotFoundError as exc:
        raise Exception("FFmpeg is not installed or not found in the system PATH.") from exc
    except Exception as exc:
        raise Exception(f"An error occurred while creating the video: {str(exc)}") from exc
    finally:
        try:
            shutil.rmtree(frames_dir)
        except Exception:
            pass

    logger.info("Done. Video is at %s.", output_file)

    return output_file

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

async def main():
    args = parse_args()
    
    result_path= await record_screen(
        html_code=args.html_code,
        url=args.url,
        output_file=args.output_file,
        duration=args.duration,
        video_framerate=args.video_framerate,
        isHorizontal=args.isHorizontal,
        audio_file=args.audio_file,
    )

    import sys
    if result_path:
        print(f"RESULT_FILE={result_path}", flush=True)
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == '__main__':
    asyncio.run(main())
