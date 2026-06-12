#!/usr/bin/env python3
"""
LinkedIn publishing via Playwright.

First run (auth setup):
    python social-media/scripts/linkedin.py --content-file post.md --mode publish
    # Opens headed browser. Log in manually. Auth state saved automatically.

Later runs:
    python social-media/scripts/linkedin.py --content-file post.md --mode publish --headless

Output:
    JSON to stdout: {"status": "success|failed", "platform": "linkedin", ...}
    Screenshots saved to social-media/screenshots/linkedin/
    Logs saved to social-media/logs/linkedin.log
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "social-media" / "scripts"
AUTH_DIR = ROOT / "social-media" / "auth"
LOG_DIR = ROOT / "social-media" / "logs"
SCREENSHOT_DIR = ROOT / "social-media" / "screenshots" / "linkedin"
POSTS_PUBLISHED = ROOT / "social-media" / "posts" / "published"
POSTS_FAILED = ROOT / "social-media" / "posts" / "failed"

AUTH_FILE = AUTH_DIR / "linkedin-auth.json"

for d in (AUTH_DIR, LOG_DIR, SCREENSHOT_DIR, POSTS_PUBLISHED, POSTS_FAILED):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

log = logging.getLogger("linkedin-publish")
log.setLevel(logging.DEBUG)

fh = logging.FileHandler(LOG_DIR / "linkedin.log")
fh.setLevel(logging.DEBUG)
fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

sh = logging.StreamHandler(sys.stderr)
sh.setLevel(logging.INFO)
sh.setFormatter(logging.Formatter("%(message)s"))

log.addHandler(fh)
log.addHandler(sh)

# ---------------------------------------------------------------------------
# Selectors (captured from browser discovery)
# ---------------------------------------------------------------------------

FEED_URL = "https://www.linkedin.com/feed/"
POST_TRIGGER_TEXT = "Start a post"  # exact match button
COMPOSER_TEXTBOX_LABEL = "Text editor for creating content"
POST_BUTTON_TEXT = "Post"  # exact match (NOT substring of "Start a post")
SUCCESS_INDICATOR = "Post successful"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_content(path: str) -> str:
    full = (ROOT / path).expanduser().resolve()
    if not full.exists():
        full = Path(path).resolve()
    content = full.read_text(encoding="utf-8").strip()
    if not content:
        raise ValueError(f"Content file is empty: {full}")
    return content


def save_result(
    status: str,
    url: str | None = None,
    screenshot: str | None = None,
    error: str | None = None,
    action: str = "publish_post",
) -> dict:
    result = {
        "status": status,
        "action": action,
        "platform": "linkedin",
        "url": url,
        "screenshot": screenshot,
        "error": error,
    }
    print(json.dumps(result, indent=2))
    return result


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_post_published(page, short_text: str) -> bool:
    """Check that the composer modal closed and success toast appeared."""
    try:
        page.wait_for_timeout(2000)
        body = page.inner_text("body")
        if SUCCESS_INDICATOR in body:
            log.info("Verification: 'Post successful' toast found.")
            return True
        # Fallback: composer modal should be gone
        modal = page.query_selector('[role="dialog"]')
        if modal is None:
            log.info("Verification: composer modal closed (fallback).")
            return True
        log.warning("Verification: composer modal still open, no success toast.")
        return False
    except Exception as exc:
        log.warning(f"Verification error: {exc}")
        return False


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------


def publish_post(content: str, headless: bool = False) -> dict:
    short_text = content[:60].replace("\n", " ")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, args=["--no-sandbox"])
        context_kwargs: dict = {}
        if AUTH_FILE.exists():
            try:
                context_kwargs["storage_state"] = str(AUTH_FILE)
                log.info("Loaded auth state from disk.")
            except Exception:
                log.warning("Could not load auth state, starting fresh.")

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        try:
            # --- Navigate ---
            log.info(f"Navigating to {FEED_URL}...")
            page.goto(FEED_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)

            # --- Auth check (URL redirect OR login form on page) ---
            needs_login = (
                "login" in page.url
                or "checkpoint" in page.url
                or page.get_by_text("Sign in").first.is_visible()
            )
            if needs_login:
                if headless:
                    raise RuntimeError("LinkedIn login required. Run without --headless first.")
                log.info("Login required. Please log in manually in the browser window.")
                log.info("Waiting up to 120 seconds...")
                page.wait_for_url(f"{FEED_URL}*", timeout=120_000)
                page.wait_for_timeout(2000)
                context.storage_state(path=str(AUTH_FILE))
                log.info("Auth state saved.")

            # --- Step 1: Click "Start a post" ---
            log.info('Looking for "Start a post" button...')
            start_btn = page.get_by_text(POST_TRIGGER_TEXT, exact=True).first
            start_btn.wait_for(state="visible", timeout=15_000)
            start_btn.click()
            page.wait_for_timeout(2000)
            log.info("Clicked post trigger. Composer should be open.")

            # --- Step 2: Fill content ---
            log.info("Filling post content...")
            textbox = page.get_by_role("textbox", name=COMPOSER_TEXTBOX_LABEL)
            textbox.wait_for(state="visible", timeout=15_000)
            textbox.fill(content)
            page.wait_for_timeout(1500)
            log.info(f"Filled {len(content)} characters.")

            # --- Step 3: Click Post ---
            log.info('Looking for "Post" button...')
            # Use exact match to avoid matching "Start a post"
            post_btn = page.locator('button:has-text("Post"):not(:has-text("Start"))').first
            post_btn.wait_for(state="visible", timeout=10_000)
            post_btn.click()
            log.info("Clicked Post.")
            page.wait_for_timeout(4000)

            # --- Verification ---
            log.info("Verifying...")
            ts = int(time.time())
            screenshot_path = str(SCREENSHOT_DIR / f"published-{ts}.png")
            page.screenshot(path=screenshot_path, full_page=True)

            ok = verify_post_published(page, content)
            if ok:
                context.storage_state(path=str(AUTH_FILE))
                browser.close()
                log.info("Publish verified — success.")
                return save_result("success", screenshot=screenshot_path)

            browser.close()
            log.error("Verification failed after publish.")
            return save_result("failed", screenshot=screenshot_path, error="Verification failed")

        except PlaywrightTimeoutError as e:
            ts = int(time.time())
            screenshot_path = str(SCREENSHOT_DIR / f"timeout-{ts}.png")
            try:
                page.screenshot(path=screenshot_path, full_page=True)
            except Exception:
                screenshot_path = ""
            browser.close()
            log.error(f"Timeout: {e}")
            return save_result("failed", screenshot=screenshot_path, error=str(e))

        except Exception as e:
            ts = int(time.time())
            screenshot_path = str(SCREENSHOT_DIR / f"error-{ts}.png")
            try:
                page.screenshot(path=screenshot_path, full_page=True)
            except Exception:
                screenshot_path = ""
            browser.close()
            log.error(f"Error: {e}")
            return save_result("failed", screenshot=screenshot_path, error=str(e))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="LinkedIn publishing via Playwright")
    parser.add_argument("--content-file", required=True, help="Path to markdown content file")
    parser.add_argument("--mode", choices=["draft", "publish", "verify-only"], default="publish")
    parser.add_argument("--headless", action="store_true", help="Run browser headless")
    parser.add_argument("--verify", dest="verify_flag", default="true")
    args = parser.parse_args()

    try:
        content = read_content(args.content_file)
    except Exception as e:
        log.error(f"Failed to read content: {e}")
        print(json.dumps({"status": "failed", "error": str(e)}))
        sys.exit(1)

    log.info(f"Content loaded: {len(content)} chars from {args.content_file}")

    if args.mode == "publish":
        result = publish_post(content, headless=args.headless)
    elif args.mode == "verify-only":
        print(json.dumps({"status": "skipped", "action": "verify-only", "platform": "linkedin"}))
        sys.exit(0)
    else:
        log.error(f"Mode '{args.mode}' not implemented yet.")
        sys.exit(1)

    if result["status"] == "success":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
