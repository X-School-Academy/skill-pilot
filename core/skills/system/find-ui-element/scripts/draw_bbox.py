#!/usr/bin/env core/bin/python
"""Draw a bounding box rectangle on an image.

Usage:
    python3 draw_bbox.py IMAGE_PATH X1 Y1 X2 Y2 OUTPUT_PATH [--color R G B] [--width N]

Examples:
    python3 draw_bbox.py screenshot.png 100 200 300 250 .skillpilot/temp/bbox.png
    python3 draw_bbox.py screenshot.png 100 200 300 250 .skillpilot/temp/bbox.png --color 0 255 0 --width 5
"""

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def draw_bbox(image_path: str, x1: int, y1: int, x2: int, y2: int,
              output_path: str, color: tuple = (255, 0, 0), width: int = 3) -> None:
    img = Image.open(image_path).copy()
    draw = ImageDraw.Draw(img)
    draw.rectangle([x1, y1, x2, y2], outline=color, width=width)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)

    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
    print(f"Bounding box: ({x1}, {y1}, {x2}, {y2})")
    print(f"Center point: ({cx}, {cy})")
    print(f"Saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Draw bounding box on image")
    parser.add_argument("image", help="Path to the input image")
    parser.add_argument("x1", type=int, help="Left x coordinate")
    parser.add_argument("y1", type=int, help="Top y coordinate")
    parser.add_argument("x2", type=int, help="Right x coordinate")
    parser.add_argument("y2", type=int, help="Bottom y coordinate")
    parser.add_argument("output", help="Path to save the output image")
    parser.add_argument("--color", type=int, nargs=3, default=[255, 0, 0],
                        metavar=("R", "G", "B"), help="Box color (default: 255 0 0)")
    parser.add_argument("--width", type=int, default=3, help="Line width (default: 3)")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    draw_bbox(args.image, args.x1, args.y1, args.x2, args.y2,
              args.output, tuple(args.color), args.width)


if __name__ == "__main__":
    main()
