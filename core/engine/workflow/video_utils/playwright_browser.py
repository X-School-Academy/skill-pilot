import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional


_SYSTEM_CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/opt/google/chrome/chrome",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/snap/bin/chromium",
    "/usr/bin/microsoft-edge",
    "/usr/bin/microsoft-edge-stable",
    "/opt/microsoft/msedge/msedge",
    "/usr/bin/brave-browser",
    "/opt/brave.com/brave/brave-browser",
)

_SYSTEM_CHROME_COMMANDS = (
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
    "microsoft-edge",
    "microsoft-edge-stable",
    "brave-browser",
)

_PLAYWRIGHT_INSTALL_LOCK = threading.Lock()
_PLAYWRIGHT_INSTALL_ATTEMPTED = False


def _is_missing_playwright_browser_error(exc: Exception) -> bool:
    message = str(exc)
    return "Executable doesn't exist" in message or "playwright install" in message


def find_system_chrome_executable() -> Optional[str]:
    configured = os.getenv("PLAYWRIGHT_CHROME_EXECUTABLE_PATH") or os.getenv("PUPPETEER_EXECUTABLE_PATH")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    for raw_path in _SYSTEM_CHROME_CANDIDATES:
        candidate = Path(raw_path)
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    for command in _SYSTEM_CHROME_COMMANDS:
        resolved = shutil.which(command)
        if resolved:
            return resolved

    return None


def _install_playwright_chromium() -> tuple[bool, str]:
    global _PLAYWRIGHT_INSTALL_ATTEMPTED

    with _PLAYWRIGHT_INSTALL_LOCK:
        if _PLAYWRIGHT_INSTALL_ATTEMPTED:
            return False, "Playwright Chromium auto-install was already attempted in this process."

        _PLAYWRIGHT_INSTALL_ATTEMPTED = True

    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = (result.stdout or "").strip()
    error = (result.stderr or "").strip()
    details = "\n".join(part for part in (output, error) if part).strip()
    return result.returncode == 0, details


async def launch_playwright_chromium(playwright, *, headless: bool = True):
    launch_args = ["--no-sandbox"]

    try:
        return await playwright.chromium.launch(headless=headless, args=launch_args)
    except Exception as exc:
        if not _is_missing_playwright_browser_error(exc):
            raise

        install_succeeded, install_details = _install_playwright_chromium()
        if install_succeeded:
            return await playwright.chromium.launch(headless=headless, args=launch_args)

        # Do we need to use system chrome as high priority, this fallback may not have a chance to hit 
        fallback_executable = find_system_chrome_executable()
        if not fallback_executable:
            raise RuntimeError(
                "Playwright browser executable is missing, auto-install failed, and no system Chrome-compatible "
                "browser was found. Run `uv run playwright install chromium` or set "
                "PLAYWRIGHT_CHROME_EXECUTABLE_PATH."
            ) from exc

        return await playwright.chromium.launch(
            headless=headless,
            executable_path=fallback_executable,
            args=launch_args,
        )
