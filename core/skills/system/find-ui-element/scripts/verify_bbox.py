#!/usr/bin/env core/bin/python
"""Crop around a bounding box for close-up verification.

Usage:
    python3 verify_bbox.py IMAGE_PATH X1 Y1 X2 Y2 OUTPUT_PATH [--padding N]

Examples:
    python3 verify_bbox.py screenshot.png 100 200 300 250 .skillpilot/temp/verify.png
    python3 verify_bbox.py screenshot.png 100 200 300 250 .skillpilot/temp/verify.png --padding 60
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def verify_bbox(image_path: str, x1: int, y1: int, x2: int, y2: int,
                output_path: str, padding: int = 40) -> None:
    img = Image.open(image_path)
    w, h = img.size

    crop_x1 = max(0, x1 - padding)
    crop_y1 = max(0, y1 - padding)
    crop_x2 = min(w, x2 + padding)
    crop_y2 = min(h, y2 + padding)

    region = img.crop((crop_x1, crop_y1, crop_x2, crop_y2))

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    region.save(output_path)

    print(f"Cropped region: ({crop_x1}, {crop_y1}, {crop_x2}, {crop_y2})")
    print(f"Crop size: {crop_x2 - crop_x1}x{crop_y2 - crop_y1}")
    print(f"Saved to: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop around bbox for verification")
    parser.add_argument("image", help="Path to the input image")
    parser.add_argument("x1", type=int, help="Left x coordinate")
    parser.add_argument("y1", type=int, help="Top y coordinate")
    parser.add_argument("x2", type=int, help="Right x coordinate")
    parser.add_argument("y2", type=int, help="Bottom y coordinate")
    parser.add_argument("output", help="Path to save the cropped output")
    parser.add_argument("--padding", type=int, default=40,
                        help="Padding around bbox in pixels (default: 40)")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    verify_bbox(args.image, args.x1, args.y1, args.x2, args.y2,
                args.output, args.padding)


if __name__ == "__main__":
    main()
