# Screenshot

Use the `screenshot` action to capture the full screen or a specific screen region. Use optional scaling to reduce image size and optional pointer markers for coordinate correction.

## Command

```json
{
  "action": "screenshot",
  "bbox": [x, y, width, height],
  "scale": 1.0,
  "draw_pointer": true,
  "pointer_style": "contrast",
  "pointer_radius": 64
}
```

## Parameters

- `bbox`: Optional `[left, top, width, height]`. If omitted, captures the entire primary screen.
- `scale`: Optional scale factor for the output image, such as `0.5` for half size.
- `draw_pointer`: Optional marker showing the current mouse pointer location.
- `pointer_style`: Optional marker style. Use `contrast` or `alert`.
- `pointer_radius`: Optional marker radius in pixels before scaling.

## Returns

The response includes:

- `filepath`: Saved screenshot image path, usually in the system temp directory.
- `width`: Output image width after scaling.
- `height`: Output image height after scaling.
- `original_width`: Screenshot width before scaling.
- `original_height`: Screenshot height before scaling.
- `scale`: Scale used for the output image.
- `mouse_position`: Current cursor coordinates.

## Coordinate Correction

When `draw_pointer` is enabled, visually verify that the marker in the screenshot matches the returned `mouse_position`. If they do not align due to scaling or bbox offsets, adjust coordinate mapping before issuing the next `input` action.
