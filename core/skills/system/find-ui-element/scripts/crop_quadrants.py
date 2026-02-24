#!/usr/bin/env core/bin/python
"""Crop an image into a grid of regions for visual inspection.

Usage:
    python3 crop_quadrants.py IMAGE_PATH OUTPUT_DIR [--grid N]

Examples:
    python3 crop_quadrants.py screenshot.png .skillpilot/temp/quadrants/
    python3 crop_quadrants.py screenshot.png .skillpilot/temp/quadrants/ --grid 3
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def crop_grid(image_path: str, output_dir: str, grid_size: int = 2) -> None:
    img = Image.open(image_path)
    w, h = img.size
    cell_w = w // grid_size
    cell_h = h // grid_size

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for row in range(grid_size):
        for col in range(grid_size):
            x1 = col * cell_w
            y1 = row * cell_h
            x2 = (col + 1) * cell_w if col < grid_size - 1 else w
            y2 = (row + 1) * cell_h if row < grid_size - 1 else h
            region = img.crop((x1, y1, x2, y2))
            name = f"r{row}_c{col}_{x1}_{y1}_{x2}_{y2}.png"
            region.save(out / name)
            print(f"Saved {name} — offset ({x1}, {y1}) size {x2 - x1}x{y2 - y1}")

    print(f"\nOriginal image: {w}x{h}")
    print(f"Grid: {grid_size}x{grid_size} ({grid_size * grid_size} regions)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop image into grid regions")
    parser.add_argument("image", help="Path to the input image")
    parser.add_argument("output_dir", help="Directory to save cropped regions")
    parser.add_argument("--grid", type=int, default=2, help="Grid size (default: 2 for 2x2)")
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    crop_grid(args.image, args.output_dir, args.grid)


if __name__ == "__main__":
    main()
