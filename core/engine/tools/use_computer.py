#!/usr/bin/env python3
import argparse
import json
import sys
import os
import tempfile
import uuid
import time
import base64
from typing import Dict, Any, List

import pyautogui
import screeninfo
from PIL import Image, ImageDraw


# Disable PyAutoGUI fail-safe to prevent accidental stops if the mouse hits a corner,
# or keep it enabled if safety is a priority. For an autonomous agent, maybe keep it?
# Let's keep it enabled but handle the FailSafeException if it happens.
# pyautogui.FAILSAFE = True

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
        else:
            result = {"error": f"Unknown action: {action}"}
            
        print(f"<output>{json.dumps(result)}</output>")
        
    except json.JSONDecodeError:
        print(f"<output>{json.dumps({'error': 'Invalid JSON string'})}</output>")
    except Exception as e:
        print(f"<output>{json.dumps({'error': str(e)})}</output>")

if __name__ == "__main__":
    main()
