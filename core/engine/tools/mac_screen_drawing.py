#!/usr/bin/env python3
import argparse
import json
import os
import signal
import sys
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass
class ScreenBounds:
    min_x: float
    min_y: float
    max_x: float
    max_y: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def height(self) -> float:
        return self.max_y - self.min_y


def _parse_bbox(value: str) -> Tuple[float, float, float, float]:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must be 'x,y,width,height'")
    x, y, width, height = [float(part) for part in parts]
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    return x, y, width, height


def _load_pyobjc() -> Dict[str, Any]:
    if sys.platform != "darwin":
        raise RuntimeError("mac_screen_drawing.py only supports macOS")

    try:
        import objc  # type: ignore
        from AppKit import (  # type: ignore
            NSApplication,
            NSBackingStoreBuffered,
            NSBezierPath,
            NSColor,
            NSMakeRect,
            NSScreen,
            NSScreenSaverWindowLevel,
            NSView,
            NSWindow,
            NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary,
            NSWindowStyleMaskBorderless,
        )
        from PyObjCTools import AppHelper  # type: ignore
    except Exception as exc:
        raise RuntimeError(f"Screen drawing unavailable (PyObjC/AppKit): {exc}") from exc

    return {
        "objc": objc,
        "NSApplication": NSApplication,
        "NSBackingStoreBuffered": NSBackingStoreBuffered,
        "NSBezierPath": NSBezierPath,
        "NSColor": NSColor,
        "NSMakeRect": NSMakeRect,
        "NSScreen": NSScreen,
        "NSScreenSaverWindowLevel": NSScreenSaverWindowLevel,
        "NSView": NSView,
        "NSWindow": NSWindow,
        "NSWindowCollectionBehaviorCanJoinAllSpaces": NSWindowCollectionBehaviorCanJoinAllSpaces,
        "NSWindowCollectionBehaviorFullScreenAuxiliary": NSWindowCollectionBehaviorFullScreenAuxiliary,
        "NSWindowStyleMaskBorderless": NSWindowStyleMaskBorderless,
        "AppHelper": AppHelper,
    }


def _screen_bounds(screens: List[Any]) -> ScreenBounds:
    min_x = min(float(screen.frame().origin.x) for screen in screens)
    min_y = min(float(screen.frame().origin.y) for screen in screens)
    max_x = max(float(screen.frame().origin.x + screen.frame().size.width) for screen in screens)
    max_y = max(float(screen.frame().origin.y + screen.frame().size.height) for screen in screens)
    return ScreenBounds(min_x=min_x, min_y=min_y, max_x=max_x, max_y=max_y)


def _top_left_bbox_to_cocoa(bounds: ScreenBounds, bbox: Tuple[float, float, float, float]) -> Tuple[float, float, float, float]:
    x, y, width, height = bbox
    cocoa_x = bounds.min_x + x
    cocoa_y = bounds.max_y - y - height
    return cocoa_x, cocoa_y, width, height


def _default_top_left_bbox(bounds: ScreenBounds) -> Tuple[float, float, float, float]:
    width = min(420.0, max(120.0, bounds.width * 0.4))
    height = min(260.0, max(80.0, bounds.height * 0.25))
    x = max(0.0, (bounds.width - width) / 2.0)
    y = max(0.0, (bounds.height - height) / 2.0)
    return x, y, width, height


def _normalize_local_rect(
    start: Tuple[float, float], end: Tuple[float, float]
) -> Tuple[float, float, float, float]:
    x1, y1 = start
    x2, y2 = end
    x = min(x1, x2)
    y = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)
    return x, y, width, height


def _point_to_tuple(point: Any) -> Tuple[float, float]:
    if hasattr(point, "x") and hasattr(point, "y"):
        return float(point.x), float(point.y)
    return float(point[0]), float(point[1])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Draw screen overlays on macOS (quick bbox mode or manual draw mode)."
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "manual"],
        default="quick",
        help="quick: show one bbox for a fixed duration; manual: draw by click-drag until stopped",
    )
    parser.add_argument(
        "--bbox",
        type=str,
        default=None,
        help="Bounding box in top-left coordinates: x,y,width,height. Used by quick mode.",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=5.0,
        help="Seconds to keep quick mode overlay visible before exit.",
    )
    parser.add_argument(
        "--state-path",
        type=str,
        default=os.getenv("SCREEN_DRAWING_STATE_PATH", ".skillpilot/temp/screen-drawing-state.json"),
        help="JSON state file for manual mode updates (last drawn bbox).",
    )

    args = parser.parse_args()

    try:
        pyobjc = _load_pyobjc()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    objc = pyobjc["objc"]
    NSApplication = pyobjc["NSApplication"]
    NSBackingStoreBuffered = pyobjc["NSBackingStoreBuffered"]
    NSBezierPath = pyobjc["NSBezierPath"]
    NSColor = pyobjc["NSColor"]
    NSMakeRect = pyobjc["NSMakeRect"]
    NSScreen = pyobjc["NSScreen"]
    NSScreenSaverWindowLevel = pyobjc["NSScreenSaverWindowLevel"]
    NSView = pyobjc["NSView"]
    NSWindow = pyobjc["NSWindow"]
    NSWindowCollectionBehaviorCanJoinAllSpaces = pyobjc[
        "NSWindowCollectionBehaviorCanJoinAllSpaces"
    ]
    NSWindowCollectionBehaviorFullScreenAuxiliary = pyobjc[
        "NSWindowCollectionBehaviorFullScreenAuxiliary"
    ]
    NSWindowStyleMaskBorderless = pyobjc["NSWindowStyleMaskBorderless"]
    AppHelper = pyobjc["AppHelper"]

    app = NSApplication.sharedApplication()
    screens = list(NSScreen.screens())
    if not screens:
        print("No displays detected.", file=sys.stderr)
        return 1

    bounds = _screen_bounds(screens)

    if args.bbox:
        try:
            quick_top_left_bbox = _parse_bbox(args.bbox)
        except ValueError as exc:
            print(f"Invalid --bbox: {exc}", file=sys.stderr)
            return 2
    else:
        quick_top_left_bbox = _default_top_left_bbox(bounds)

    quick_cocoa_bbox = _top_left_bbox_to_cocoa(bounds, quick_top_left_bbox)

    state_path = os.path.abspath(args.state_path)
    state: Dict[str, Any] = {
        "mode": args.mode,
        "active": False,
        "windows": [],
        "stopping": False,
        "state_path": state_path,
    }

    def _write_manual_state(bbox_top_left: Tuple[float, float, float, float]) -> None:
        parent = os.path.dirname(state_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        payload = {
            "mode": "manual",
            "updated_at": time.time(),
            "last_bbox": {
                "x": int(round(bbox_top_left[0])),
                "y": int(round(bbox_top_left[1])),
                "width": int(round(bbox_top_left[2])),
                "height": int(round(bbox_top_left[3])),
            },
        }

        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True)

    class OverlayView(NSView):
        def initWithFrame_(self, frame):
            self = objc.super(OverlayView, self).initWithFrame_(frame)
            if self is None:
                return None
            self._screen_origin = (0.0, 0.0)
            self._interactive = False
            self._fixed_cocoa_rect = None
            self._drag_start = None
            self._drag_end = None
            self._manual_rects = []
            return self

        def isOpaque(self):
            return False

        def acceptsFirstMouse_(self, _event):
            return True

        def configure_(self, config):
            self._screen_origin = config.get("screen_origin", (0.0, 0.0))
            self._interactive = bool(config.get("interactive", False))
            self._fixed_cocoa_rect = config.get("fixed_cocoa_rect")
            self.setNeedsDisplay_(True)

        def _draw_rect(self, rect, color):
            x, y, width, height = rect
            if width < 1 or height < 1:
                return
            color.setStroke()
            path = NSBezierPath.bezierPathWithRect_(NSMakeRect(x, y, width, height))
            path.setLineWidth_(2.0)
            path.stroke()

        def _draw_fixed_if_present(self):
            if self._fixed_cocoa_rect is None:
                return
            fixed_x, fixed_y, fixed_width, fixed_height = self._fixed_cocoa_rect
            local_x = fixed_x - self._screen_origin[0]
            local_y = fixed_y - self._screen_origin[1]
            self._draw_rect((local_x, local_y, fixed_width, fixed_height), NSColor.redColor())

        def drawRect_(self, _rect):
            self._draw_fixed_if_present()

            for manual_rect in self._manual_rects:
                self._draw_rect(manual_rect, NSColor.systemGreenColor())

            if self._drag_start is not None and self._drag_end is not None:
                preview = _normalize_local_rect(self._drag_start, self._drag_end)
                self._draw_rect(preview, NSColor.systemYellowColor())

        def mouseDown_(self, event):
            if not self._interactive:
                return
            point = self.convertPoint_fromView_(event.locationInWindow(), None)
            self._drag_start = _point_to_tuple(point)
            self._drag_end = self._drag_start
            self.setNeedsDisplay_(True)

        def mouseDragged_(self, event):
            if not self._interactive or self._drag_start is None:
                return
            point = self.convertPoint_fromView_(event.locationInWindow(), None)
            self._drag_end = _point_to_tuple(point)
            self.setNeedsDisplay_(True)

        def mouseUp_(self, event):
            if not self._interactive or self._drag_start is None:
                return

            point = self.convertPoint_fromView_(event.locationInWindow(), None)
            self._drag_end = _point_to_tuple(point)
            local_rect = _normalize_local_rect(self._drag_start, self._drag_end)
            self._drag_start = None
            self._drag_end = None

            if local_rect[2] < 1 or local_rect[3] < 1:
                self.setNeedsDisplay_(True)
                return

            self._manual_rects.append(local_rect)

            local_x, local_y, width, height = local_rect
            global_cocoa_x = self._screen_origin[0] + local_x
            global_cocoa_y = self._screen_origin[1] + local_y

            top_left_x = global_cocoa_x - bounds.min_x
            top_left_y = bounds.max_y - (global_cocoa_y + height)
            bbox_top_left = (top_left_x, top_left_y, width, height)

            try:
                _write_manual_state(bbox_top_left)
            except Exception as exc:
                print(f"Failed to write state file {state_path}: {exc}", file=sys.stderr, flush=True)

            print(
                json.dumps(
                    {
                        "event": "draw_end",
                        "bbox": {
                            "x": int(round(top_left_x)),
                            "y": int(round(top_left_y)),
                            "width": int(round(width)),
                            "height": int(round(height)),
                        },
                        "state_path": state_path,
                    },
                    ensure_ascii=True,
                ),
                flush=True,
            )
            self.setNeedsDisplay_(True)

    class OverlayWindow(NSWindow):
        def initWithFrame_(self, frame):
            style = NSWindowStyleMaskBorderless
            self = objc.super(OverlayWindow, self).initWithContentRect_styleMask_backing_defer_(
                frame,
                style,
                NSBackingStoreBuffered,
                False,
            )
            if self is None:
                return None
            self.setOpaque_(False)
            self.setBackgroundColor_(NSColor.clearColor())
            self.setHasShadow_(False)
            self.setLevel_(NSScreenSaverWindowLevel)
            self.setCollectionBehavior_(
                NSWindowCollectionBehaviorCanJoinAllSpaces
                | NSWindowCollectionBehaviorFullScreenAuxiliary
            )
            self.setReleasedWhenClosed_(False)
            return self

    def _shutdown() -> None:
        if state["stopping"]:
            return
        state["stopping"] = True

        for window in state.get("windows", []):
            try:
                window.orderOut_(None)
                window.close()
            except Exception:
                pass

        state["windows"] = []
        state["active"] = False

        try:
            AppHelper.stopEventLoop()
        except Exception:
            pass

    def _on_signal(_signum, _frame):
        _shutdown()

    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try:
            signal.signal(sig, _on_signal)
        except Exception:
            pass

    interactive = args.mode == "manual"

    for screen in screens:
        frame = screen.frame()
        screen_origin = (float(frame.origin.x), float(frame.origin.y))

        view = OverlayView.alloc().initWithFrame_(NSMakeRect(0, 0, frame.size.width, frame.size.height))
        view.configure_(
            {
                "screen_origin": screen_origin,
                "interactive": interactive,
                "fixed_cocoa_rect": quick_cocoa_bbox if args.mode == "quick" else None,
            }
        )

        window = OverlayWindow.alloc().initWithFrame_(frame)
        window.setContentView_(view)
        window.setIgnoresMouseEvents_(not interactive)
        window.orderFrontRegardless()

        state["windows"].append(window)

    state["active"] = True

    if args.mode == "quick":
        duration = max(0.1, args.duration)
        print(
            json.dumps(
                {
                    "status": "running",
                    "mode": "quick",
                    "duration": duration,
                    "bbox": {
                        "x": int(round(quick_top_left_bbox[0])),
                        "y": int(round(quick_top_left_bbox[1])),
                        "width": int(round(quick_top_left_bbox[2])),
                        "height": int(round(quick_top_left_bbox[3])),
                    },
                },
                ensure_ascii=True,
            ),
            flush=True,
        )
        AppHelper.callLater(duration, _shutdown)
    else:
        print(
            json.dumps(
                {
                    "status": "running",
                    "mode": "manual",
                    "state_path": state_path,
                    "hint": "Drag with mouse to draw rectangles. Stop the process when done.",
                },
                ensure_ascii=True,
            ),
            flush=True,
        )

    try:
        AppHelper.runEventLoop()
    finally:
        _shutdown()

    if args.mode == "quick":
        print(
            json.dumps({"status": "completed", "mode": "quick"}, ensure_ascii=True),
            flush=True,
        )
    else:
        print(
            json.dumps({"status": "stopped", "mode": "manual"}, ensure_ascii=True),
            flush=True,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
