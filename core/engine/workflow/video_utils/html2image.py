# file: pyppeteer/html2image.py
import asyncio
import argparse
import uuid
import sys
import os
import aiofiles
from playwright.async_api import async_playwright
from workflow.video_utils.playwright_browser import launch_playwright_chromium

async def capture_image(
    html_code,
    isHorizontal=False,
    view_width=None,
    view_height=None,
    omitBackground=False,
    timeout=10,
    retries=3,
):
    """
    The actual logic to launch Playwright, take a screenshot, etc.
    Returns the path to the final image if successful, otherwise None.
    """

    width, height = (1920, 1080) if isHorizontal else (1080, 1920)

    if view_width is not None and view_height is not None:
        width = view_width
        height = view_height

    image_file = f"/tmp/code_image_{uuid.uuid4()}.png"

    # for debugging purposes, write the HTML code to a temporary file
    html_file = f'/tmp/video_image_{str(uuid.uuid4())}.html'
    async with aiofiles.open(html_file, 'w') as f:
        await f.write(html_code)
        print(f"html_file: {html_file}")

    # Retry logic
    for attempt in range(1, retries + 1):
        browser = None
        playwright = None
        capture_task = None

        try:
            playwright = await async_playwright().start()
            browser = await launch_playwright_chromium(playwright, headless=True)

            # Create a task that we can cancel if needed
            async def capture():
                page = await browser.new_page()
                await page.set_viewport_size({'width': width, 'height': height})
                await page.set_content(html_code)
                await page.screenshot(path=image_file, omit_background=omitBackground)
                return image_file

            capture_task = asyncio.create_task(capture())
            result = await asyncio.wait_for(capture_task, timeout=timeout)

            # Success - clean up and return
            if os.path.exists(html_file):
                os.remove(html_file)
            return result

        except asyncio.TimeoutError:
            print(f"[html2image.py] Timeout on attempt {attempt}", file=sys.stderr)
            # Cancel the task if it's still running
            if capture_task and not capture_task.done():
                capture_task.cancel()
                try:
                    await capture_task
                except (asyncio.CancelledError, Exception):
                    pass
        except Exception as exc:
            print(f"[html2image.py] Error on attempt {attempt}: {exc}", file=sys.stderr)
        finally:
            # Clean up browser and playwright resources after each attempt
            if browser is not None:
                try:
                    await browser.close()
                except Exception as e:
                    print(f"[html2image.py] Error closing browser: {e}", file=sys.stderr)
            if playwright is not None:
                try:
                    await playwright.stop()
                except Exception as e:
                    print(f"[html2image.py] Error stopping playwright: {e}", file=sys.stderr)

    # All retries failed - clean up HTML file
    if os.path.exists(html_file):
        os.remove(html_file)
    return None

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--html_code", required=True, help="Inline HTML code to render.")
    parser.add_argument("--isHorizontal", action="store_true", help="Landscape vs portrait.")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout per attempt.")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries.")

    args = parser.parse_args()

    result_path = await capture_image(
        html_code=args.html_code,
        isHorizontal=args.isHorizontal,
        timeout=args.timeout,
        retries=args.retries,
    )

    # If successful, print the path with a marker so the caller can parse it
    if result_path:
        print(f"RESULT_FILE={result_path}", flush=True)
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
