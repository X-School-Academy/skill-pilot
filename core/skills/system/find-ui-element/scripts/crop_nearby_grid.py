#!/usr/bin/env core/bin/python
"""Crop a nearby search window into a fixed grid for local retry.

Usage:
    python3 crop_nearby_grid.py IMAGE_PATH X1 Y1 X2 Y2 OUTPUT_DIR [--grid N] [--expand K]

Examples:
    python3 crop_nearby_grid.py screenshot.png 100 200 180 240 .skillpilot/temp/nearby/ --grid 2
    python3 crop_nearby_grid.py screenshot.png 100 200 180 240 .skillpilot/temp/nearby/ --grid 3 --expand 6
"""

import argparse
import sys
from pathlib import Path

from PIL import Image


def _clip(val: int, low: int, high: int) -> int:
    return max(low, min(val, high))


def crop_nearby_grid(
    image_path: str,
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    output_dir: str,
    grid_size: int = 2,
    expand_factor: float = 6.0,
) -> None:
    img = Image.open(image_path)
    img_w, img_h = img.size

    # Normalize and clip bbox into image bounds.
    bx1, bx2 = sorted((x1, x2))
    by1, by2 = sorted((y1, y2))
    bx1 = _clip(bx1, 0, img_w)
    bx2 = _clip(bx2, 0, img_w)
    by1 = _clip(by1, 0, img_h)
    by2 = _clip(by2, 0, img_h)

    bw = max(1, bx2 - bx1)
    bh = max(1, by2 - by1)
    cx = (bx1 + bx2) // 2
    cy = (by1 + by2) // 2

    # Nearby search window centered on prior estimate.
    min_w = max(1, img_w // 3)
    min_h = max(1, img_h // 3)
    win_w = min(img_w, max(min_w, int(round(bw * expand_factor))))
    win_h = min(img_h, max(min_h, int(round(bh * expand_factor))))

    win_x1 = _clip(cx - win_w // 2, 0, img_w - win_w)
    win_y1 = _clip(cy - win_h // 2, 0, img_h - win_h)
    win_x2 = win_x1 + win_w
    win_y2 = win_y1 + win_h

    window = img.crop((win_x1, win_y1, win_x2, win_y2))

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    cell_w = max(1, win_w // grid_size)
    cell_h = max(1, win_h // grid_size)

    for row in range(grid_size):
        for col in range(grid_size):
            lx1 = col * cell_w
            ly1 = row * cell_h
            lx2 = (col + 1) * cell_w if col < grid_size - 1 else win_w
            ly2 = (row + 1) * cell_h if row < grid_size - 1 else win_h

            gx1 = win_x1 + lx1
            gy1 = win_y1 + ly1
            gx2 = win_x1 + lx2
            gy2 = win_y1 + ly2

            region = window.crop((lx1, ly1, lx2, ly2))
            name = f"nr{row}_c{col}_{gx1}_{gy1}_{gx2}_{gy2}.png"
            region.save(out / name)
            print(f"Saved {name} — offset ({gx1}, {gy1}) size {gx2 - gx1}x{gy2 - gy1}")

    print(f"\nImage: {img_w}x{img_h}")
    print(f"Prior bbox: ({bx1}, {by1}, {bx2}, {by2})")
    print(f"Nearby window: ({win_x1}, {win_y1}, {win_x2}, {win_y2})")
    print(f"Grid: {grid_size}x{grid_size} ({grid_size * grid_size} regions)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Crop nearby search window into grid regions")
    parser.add_argument("image", help="Path to the input image")
    parser.add_argument("x1", type=int, help="Prior bbox left x")
    parser.add_argument("y1", type=int, help="Prior bbox top y")
    parser.add_argument("x2", type=int, help="Prior bbox right x")
    parser.add_argument("y2", type=int, help="Prior bbox bottom y")
    parser.add_argument("output_dir", help="Directory to save cropped regions")
    parser.add_argument("--grid", type=int, default=2, help="Grid size (default: 2)")
    parser.add_argument(
        "--expand",
        type=float,
        default=6.0,
        help="Nearby window scale relative to bbox size (default: 6.0)",
    )
    args = parser.parse_args()

    if not Path(args.image).exists():
        print(f"Error: Image not found: {args.image}", file=sys.stderr)
        sys.exit(1)
    if args.grid < 2:
        print("Error: --grid must be >= 2", file=sys.stderr)
        sys.exit(1)
    if args.expand <= 0:
        print("Error: --expand must be > 0", file=sys.stderr)
        sys.exit(1)

    crop_nearby_grid(
        args.image,
        args.x1,
        args.y1,
        args.x2,
        args.y2,
        args.output_dir,
        grid_size=args.grid,
        expand_factor=args.expand,
    )


if __name__ == "__main__":
    main()
