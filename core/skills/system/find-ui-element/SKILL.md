---
name: find-ui-element
description: Find UI elements (buttons, links, dropdowns, checkboxes, radio buttons, text inputs, etc.) in screenshots by visual inspection, bounding box drawing, and crop verification. Use for computer-use tasks, UI automation, and visual element location.
---

# AI Builder - Find UI Element

Locate any clickable or interactive UI element in a screenshot — buttons, links, dropdowns, checkboxes, radio buttons, text input areas, etc. Uses a vision-first approach:
1. find quickly from the full image,
2. verify with a small close-up crop,
3. if wrong, retry with fixed-grid crops in nearby regions.

## When to Use This Skill

- Locating any clickable element (button, link, dropdown, checkbox, radio button) in a screenshot
- Finding text input areas (search boxes, form fields, text areas) for typing automation
- Getting pixel coordinates of a UI element for computer-use tasks
- Verifying element positions before automated interaction

## Your Roles in This Skill

- **QA Engineer**: Visually inspect screenshots, locate target elements, and verify bounding box accuracy.

## Role Communication

As an expert in your assigned roles, you must announce your actions before performing them using the following format:

As a {Role}, I will {action description}

This communication pattern ensures transparency and allows for human-in-the-loop oversight at key decision points.

## Instructions

Follow these steps in order.

Retry policy:
- `MAX_TRIES = 4` total attempts (1 initial + up to 3 retries)
- Stop early when the verification crop clearly confirms the element
- If all tries fail, report failure explicitly (element may be absent or not visually identifiable)

### Step 1: Load and View the Screenshot

Load the screenshot and note its dimensions. Then **visually inspect** the full image to estimate where the target element is.

```bash
core/bin/python -c "from PIL import Image; img = Image.open('INPUT_PATH'); print(f'Dimensions: {img.size[0]}x{img.size[1]}')"
```

### Step 2: Estimate Coordinates by Vision

Look at the full screenshot and estimate the bounding box `(x1, y1, x2, y2)` of the target element based on visual inspection. Use the image dimensions to guide your estimate.

### Step 3: Draw and Verify (Small Area First)

Draw the bounding box, then crop around it to verify.

```bash
core/bin/python core/skills/system/find-ui-element/scripts/draw_bbox.py INPUT_PATH x1 y1 x2 y2 .skillpilot/temp/bbox-TIMESTAMP.png
core/bin/python core/skills/system/find-ui-element/scripts/verify_bbox.py INPUT_PATH x1 y1 x2 y2 .skillpilot/temp/verify-TIMESTAMP.png --padding 24
```

- `draw_bbox.py` options: `--color R G B` (default: 255 0 0), `--width N` (default: 3)
- `verify_bbox.py` options: `--padding N` pixels of context (default: 40). Prefer a small padding first (for example `24`) to make small targets easier to inspect.

Visually inspect the verification crop. If the bbox correctly covers the target element, go to **Step 5**.

### Step 4: Refine with Fixed-Grid Nearby Crops (if verification failed)

If the coordinates were wrong, retry by narrowing to nearby regions using a fixed grid around the **last failed bbox**. Principle: finding a small element is easier in a small area than in the full screen.

```bash
core/bin/python core/skills/system/find-ui-element/scripts/crop_nearby_grid.py INPUT_PATH LAST_X1 LAST_Y1 LAST_X2 LAST_Y2 .skillpilot/temp/crops-TIMESTAMP/ --grid N
```

**Choose the crop fraction based on how far off you were:**

| Retry try | Grid | Crop size | When to use |
|---|---|---|---|
| Retry 1 | `--grid 2` | 4 regions in nearby window | Initial estimate clearly far off |
| Retry 2 | `--grid 3` | 9 regions in nearby window | Estimate is in roughly correct neighborhood |
| Retry 3 | `--grid 4` | 16 regions in nearby window | Need fine local search for a small target |

1. Generate nearby crops around the last failed bbox using `crop_nearby_grid.py`.
2. Choose the crop nearest to the last estimate (filename includes full-image coordinates: `..._x1_y1_x2_y2.png`).
3. Re-estimate `(x1, y1, x2, y2)` in **full-image coordinates** (directly from the crop filename offsets).
4. Go back to **Step 3** and verify again with a small padding crop.
5. Increase grid granularity on each retry (`2 -> 3 -> 4`), up to `MAX_TRIES`.
6. If still not found after max tries, output a failure result instead of guessing.

Fallback (optional, final attempt only):
- If nearby retries repeatedly fail because the initial region was completely wrong, run a one-time global grid scan:
```bash
core/bin/python core/skills/system/find-ui-element/scripts/crop_quadrants.py INPUT_PATH .skillpilot/temp/global-crops-TIMESTAMP/ --grid 2
```
- Use this only as a final recovery step within `MAX_TRIES`.

### Step 5: Output Final Coordinates

If verified, report confirmed coordinates:
- `(x1, y1, x2, y2)` — bounding box
- `(cx, cy)` — center point (for click targets): `cx = (x1+x2)//2, cy = (y1+y2)//2`

If not verified after `MAX_TRIES`, report:
- `status: not_found`
- `reason: verification_failed_after_max_tries`
- `last_attempt_bbox: (x1, y1, x2, y2)` (optional)

## Expected Output

- Bounding box coordinates: `(x1, y1, x2, y2)`
- Center point coordinates: `(cx, cy)`
- Annotated screenshot with the bounding box drawn on it
- Verification crop showing close-up of the located element

## Key Principles

- **Vision first**: Always attempt to estimate coordinates from the full image before cropping
- **Small verify crop first**: Start with a tight verification crop to validate tiny elements
- **Crop only on failure**: Only crop into regions when verification shows the estimate was wrong
- **Fixed-grid retries**: Use deterministic retry schedule (`grid 2 -> 3 -> 4`) instead of ad hoc searching
- **Bounded attempts**: Never keep guessing indefinitely; stop at `MAX_TRIES`
- **All coordinates in original image space**: When estimating from a crop, always convert back using the offset
- **Temp files**: Save all intermediate images to `.skillpilot/temp/` with descriptive, timestamped names
