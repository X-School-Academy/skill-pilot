#!/usr/bin/env python3
import argparse
import json
import sys
import os
import platform
import shlex
import subprocess
import tempfile
import uuid
import time
import base64
from typing import Dict, Any, List, Optional, Tuple

import pyautogui
import screeninfo
from PIL import Image, ImageDraw


# Disable PyAutoGUI fail-safe to prevent accidental stops if the mouse hits a corner,
# or keep it enabled if safety is a priority. For an autonomous agent, maybe keep it?
# Let's keep it enabled but handle the FailSafeException if it happens.
# pyautogui.FAILSAFE = True

DEFAULT_MAC_TERMINAL_WIDTH = 1920
DEFAULT_MAC_TERMINAL_HEIGHT = 1080


def run_osascript(script: str) -> str:
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def apple_script_string(value: str) -> str:
    return json.dumps(value)


def ensure_macos() -> Optional[Dict[str, str]]:
    if platform.system() != "Darwin":
        return {"error": "This action is only supported on macOS"}
    return None


def get_primary_screen_bounds() -> Tuple[int, int, int, int]:
    monitors = screeninfo.get_monitors()
    primary = next((m for m in monitors if m.is_primary), None)
    if primary:
        return primary.x, primary.y, primary.width, primary.height

    width, height = pyautogui.size()
    return 0, 0, width, height


def get_mac_terminal_window_bounds(window_id: int) -> Tuple[int, int, int, int]:
    script = f'''
    tell application "Terminal"
        if not (exists (first window whose id is {window_id})) then
            error "Terminal window {window_id} does not exist"
        end if
        set theWindow to first window whose id is {window_id}
        set index of theWindow to 1
        set b to bounds of theWindow
        set windowWidth to (item 3 of b) - (item 1 of b)
        set windowHeight to (item 4 of b) - (item 2 of b)
        return (item 1 of b as text) & "," & (item 2 of b as text) & "," & (windowWidth as text) & "," & (windowHeight as text)
    end tell
    '''
    out = run_osascript(script)
    return tuple(map(int, out.split(",")))


def wait_for_mac_terminal_window(window_id: int, timeout: float = 10.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            out = run_osascript(f'''
            tell application "Terminal"
                if exists (first window whose id is {window_id}) then
                    return "ok"
                end if
            end tell
            ''')
            if out == "ok":
                return
        except subprocess.CalledProcessError:
            pass
        time.sleep(0.2)
    raise TimeoutError(f"Terminal window {window_id} did not appear.")


def mac_open_native_terminal(params: Dict[str, Any]) -> Dict[str, Any]:
    mac_error = ensure_macos()
    if mac_error:
        return mac_error

    if "tmux_session_id" in params:
        tmux_session_id = params.get("tmux_session_id")
    else:
        tmux_session_id = params.get("session_id")
    if tmux_session_id is None:
        tmux_session_id = f"use_computer_{uuid.uuid4().hex[:8]}"
    if not isinstance(tmux_session_id, str) or not tmux_session_id.strip():
        return {"error": "tmux_session_id must be a non-empty string"}
    tmux_session_id = tmux_session_id.strip()

    width = int(params.get("width", DEFAULT_MAC_TERMINAL_WIDTH))
    height = int(params.get("height", DEFAULT_MAC_TERMINAL_HEIGHT))
    timeout = float(params.get("timeout", 10.0))

    screen_x, screen_y, screen_w, screen_h = get_primary_screen_bounds()
    window_w = min(width, screen_w)
    window_h = min(height, screen_h)
    x = screen_x + max(0, int((screen_w - window_w) / 2))
    y = screen_y + max(0, int((screen_h - window_h) / 2))

    unique_title = f"USE_COMPUTER_TERM_{uuid.uuid4().hex[:8]}"
    tmux_command = "printf '\\033]0;{}\\007'; exec tmux new-session -A -s {}".format(
        unique_title,
        shlex.quote(tmux_session_id),
    )
    script = f'''
    tell application "Terminal"
        activate
        do script {apple_script_string(tmux_command)}
        delay 0.5
        set theWindow to front window
        return (id of theWindow as text)
    end tell
    '''

    try:
        window_id = int(run_osascript(script))
        wait_for_mac_terminal_window(window_id, timeout=timeout)

        resize_script = f'''
        tell application "Terminal" to activate
        delay 0.2
        tell application "Terminal"
            set theWindow to first window whose id is {window_id}
            set index of theWindow to 1
            set bounds of theWindow to {{{x}, {y}, {x + window_w}, {y + window_h}}}
        end tell
        '''
        run_osascript(resize_script)
        time.sleep(0.5)

        bounds = get_mac_terminal_window_bounds(window_id)
        return {
            "window_id": window_id,
            "tmux_session_id": tmux_session_id,
            "bbox": list(bounds),
            "window_bounds": {
                "x": bounds[0],
                "y": bounds[1],
                "width": bounds[2],
                "height": bounds[3],
            },
        }
    except subprocess.CalledProcessError as e:
        return {"error": e.stderr.strip() or str(e)}
    except Exception as e:
        return {"error": str(e)}


def mac_close_native_terminal(params: Dict[str, Any]) -> Dict[str, Any]:
    mac_error = ensure_macos()
    if mac_error:
        return mac_error

    window_id = params.get("window_id")
    if window_id is None:
        return {"error": "window_id is required"}

    try:
        window_id = int(window_id)
    except (TypeError, ValueError):
        return {"error": "window_id must be an integer"}

    script = f'''
    tell application "Terminal"
        if exists (first window whose id is {window_id}) then
            close (first window whose id is {window_id}) saving no
            return "closed"
        end if
        return "not_found"
    end tell
    '''
    try:
        status = run_osascript(script)
        return {"window_id": window_id, "status": status}
    except subprocess.CalledProcessError as e:
        return {"window_id": window_id, "status": "error", "error": e.stderr.strip() or str(e)}


def get_screen_info() -> Dict[str, Any]:
    monitors = screeninfo.get_monitors()
    monitor_data = []
    for m in monitors:
        monitor_data.append({
            "x": m.x,
            "y": m.y,
            "width": m.width,
            "height": m.height,
            "is_primary": m.is_primary,
            "name": m.name
        })
    
    # Also get primary screen size from pyautogui as a fallback/confirmation
    width, height = pyautogui.size()
    
    return {
        "monitors": monitor_data,
        "primary_size": {"width": width, "height": height},
        "count": len(monitors)
    }

def get_screenshot(params: Dict[str, Any]) -> Dict[str, Any]:
    bbox = params.get("bbox") # [x, y, width, height]
    scale = params.get("scale", 1.0)
    draw_pointer = params.get("draw_pointer", False)
    pointer_radius = params.get("pointer_radius", 8)
    pointer_style = params.get("pointer_style", "contrast")
    
    region = None
    if bbox and len(bbox) == 4:
        region = (bbox[0], bbox[1], bbox[2], bbox[3])
    
    try:
        mouse_x, mouse_y = pyautogui.position()
        # pyautogui.screenshot() returns a PIL Image
        img = pyautogui.screenshot(region=region)

        # Save original dimensions before scaling
        original_width = img.width
        original_height = img.height

        if scale != 1.0 and scale > 0:
            new_width = int(img.width * scale)
            new_height = int(img.height * scale)
            img = img.resize((new_width, new_height), Image.LANCZOS)

        if draw_pointer:
            if pointer_style == "alert":
                pointer_border_color = "#ff3b30"
                pointer_fill_color = (255, 214, 10, 128)  # Semi-transparent yellow (RGBA)
            else:
                pointer_border_color = "#ffffff"
                pointer_fill_color = (0, 0, 0, 128)  # Semi-transparent black (RGBA)

            # Calculate pointer position relative to the screenshot region.
            rel_x, rel_y = mouse_x, mouse_y
            if region:
                rel_x = mouse_x - region[0]
                rel_y = mouse_y - region[1]

            # Only draw if the pointer is within the captured region bounds (use original dimensions).
            bounds_width = region[2] if region else original_width
            bounds_height = region[3] if region else original_height
            if 0 <= rel_x < bounds_width and 0 <= rel_y < bounds_height:
                # Convert to RGBA to support transparency
                img = img.convert("RGBA")
                draw = ImageDraw.Draw(img, "RGBA")

                scaled_x = rel_x * scale
                scaled_y = rel_y * scale
                scaled_radius = max(1, int(pointer_radius * scale))
                border_width = max(1, int(scaled_radius / 5))

                left = scaled_x - scaled_radius
                top = scaled_y - scaled_radius
                right = scaled_x + scaled_radius
                bottom = scaled_y + scaled_radius

                # Draw semi-transparent filled circle with border
                draw.ellipse([left, top, right, bottom], fill=pointer_fill_color, outline=pointer_border_color, width=border_width)
        
        # Save to temp file
        tmp_dir = tempfile.gettempdir()
        filename = f"use_computer_{uuid.uuid4()}.png"
        filepath = os.path.join(tmp_dir, filename)
        
        img.save(filepath)
        
        return {
            "filepath": filepath,
            "width": img.width,
            "height": img.height,
            "original_width": int(img.width / scale) if scale != 1.0 else img.width,
            "original_height": int(img.height / scale) if scale != 1.0 else img.height,
            "scale": scale,
            "mouse_position": {"x": mouse_x, "y": mouse_y}
        }
    except Exception as e:
        return {"error": str(e)}

def perform_actions(params: Dict[str, Any]) -> Dict[str, Any]:
    actions = params.get("actions", [])
    results = []
    
    for action in actions:
        action_type = action.get("type")
        try:
            if action_type == "mouse_move":
                x = action.get("x")
                y = action.get("y")
                duration = action.get("duration", 0.0)
                pyautogui.moveTo(x, y, duration=duration)
                results.append({"type": action_type, "status": "success"})
                
            elif action_type == "click":
                button = action.get("button", "left")
                clicks = action.get("clicks", 1)
                interval = action.get("interval", 0.0)
                x = action.get("x") # Optional, move before click
                y = action.get("y")
                pyautogui.click(x=x, y=y, clicks=clicks, interval=interval, button=button)
                results.append({"type": action_type, "status": "success"})
                
            elif action_type == "type":
                text = action.get("text")
                interval = action.get("interval", 0.0)
                pyautogui.write(text, interval=interval)
                results.append({"type": action_type, "status": "success"})
                
            elif action_type == "key":
                keys = action.get("keys") # List of keys or single key string
                if isinstance(keys, str):
                    keys = [keys]
                interval = action.get("interval", 0.0)
                pyautogui.press(keys, interval=interval)
                results.append({"type": action_type, "status": "success"})
            
            elif action_type == "hotkey":
                keys = action.get("keys") # List of keys e.g. ['ctrl', 'c']
                if isinstance(keys, str):
                     # If string, try to split or treat as single, but hotkey expects args
                     keys = [keys]
                pyautogui.hotkey(*keys)
                results.append({"type": action_type, "status": "success"})

            elif action_type == "wait":
                duration = action.get("duration", 1.0)
                time.sleep(duration)
                results.append({"type": action_type, "status": "success"})
                
            else:
                results.append({"type": action_type, "status": "error", "message": "Unknown action type"})
                
        except Exception as e:
             results.append({"type": action_type, "status": "error", "message": str(e)})
             # Stop processing further actions on error? Or continue? 
             # Let's continue but report error
    
    return {"results": results}

def main():
    parser = argparse.ArgumentParser(description="Use Computer Skill Agent")
    parser.add_argument("--json_str", type=str, required=True, help="JSON input string")
    
    args = parser.parse_args()
    
    try:
        input_data = json.loads(args.json_str)
        action = input_data.get("action")
        
        result = {}
        
        if action == "screen_info":
            result = get_screen_info()
        elif action == "screenshot":
            result = get_screenshot(input_data)
        elif action == "input":
            result = perform_actions(input_data)
        elif action == "mac_open_native_terminal":
            result = mac_open_native_terminal(input_data)
        elif action == "mac_close_native_terminal":
            result = mac_close_native_terminal(input_data)
        else:
            result = {"error": f"Unknown action: {action}"}
            
        print(f"<output>{json.dumps(result)}</output>")
        
    except json.JSONDecodeError:
        print(f"<output>{json.dumps({'error': 'Invalid JSON string'})}</output>")
    except Exception as e:
        print(f"<output>{json.dumps({'error': str(e)})}</output>")

if __name__ == "__main__":
    main()
