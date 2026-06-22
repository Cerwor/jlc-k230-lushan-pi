# Circle Detection Patterns

Use this reference when a contest task needs circles, rings, round targets, balls, coins, or circular marks on the LCKFB/JLC Lushan Pi K230.

Official sources:

- https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-feature-detect.html
- https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/openmv/image_module_api.html

For failures, use `troubleshooting.md#camera-problems` and `troubleshooting.md#contest-integration-problems`.

## Contents

- Default Display Strategy
- Performance Rules
- Dual-Channel Pattern
- ROI and Coordinates
- Printing and Telemetry
- Display Layer Tradeoff
- Built-In Template

## Default Display Strategy

If the user says "3.1-inch screen display" or "LCD display", default to full-screen `800x480` output on the ST7701 LCD.

Do not silently center a `400x240` processing image on the `800x480` LCD. If a small image is intentionally shown, say it is a centered debug view. For final contest display, prefer full-screen camera preview with scaled overlay.

## Performance Rules

`find_circles` uses a Hough-transform style search and is very expensive. Do not run it over the full `800x480` frame by default.

Prefer:

- Detect at `400x240` or `320x240`.
- Use a small ROI such as `ROI = (80, 40, 240, 160)` in a `400x240` detection image.
- Increase `x_stride` and `y_stride` for larger circles.
- Run detection every `N` frames and reuse the last result for overlay.
- Filter by radius and magnitude after detection.
- If a real round target such as a bottle cap is missed, lower the Hough threshold and stride before changing the display architecture. On the tested board, `threshold=1200` and `x_stride=y_stride=2` detected a bottle cap where `threshold=2500` and stride `4` did not.
- When multiple round candidates appear, keep separate raw-detection and tracked-target telemetry. Prefer a previous-center gate plus short result hold over switching immediately to a far candidate with a higher Hough magnitude.
- Disable per-frame `print(...)` in the real-time loop unless explicitly debugging.

## Dual-Channel Pattern

Use two camera channels when full-screen display and lower-resolution detection are both needed:

```text
CH0: 800x480 RGB565 for full-screen LCD display and overlay
CH1: 400x240 or 320x240 GRAYSCALE/RGB565 for circle detection
```

Map detection coordinates back to LCD/display coordinates:

```python
SCALE_X = DISPLAY_WIDTH / DETECT_WIDTH
SCALE_Y = DISPLAY_HEIGHT / DETECT_HEIGHT
lcd_x = int(circle.x() * SCALE_X)
lcd_y = int(circle.y() * SCALE_Y)
lcd_r = int(circle.r() * (SCALE_X + SCALE_Y) / 2)
```

## ROI and Coordinates

Be explicit about coordinate space:

- Detection ROI coordinates are in the detection image, not the LCD image.
- Overlay coordinates are in the LCD/display image.
- UART/control coordinates should state whether they are detection coordinates or LCD coordinates.

Default for generated contest code:

- Draw overlays in LCD/display coordinates.
- Send LCD coordinates over UART unless the user asks for raw detection coordinates.
- If serial debugging is enabled, print both coordinate spaces every `N` frames.

Example detection ROI for `400x240`:

```python
CIRCLE_ROI = (80, 40, 240, 160)
```

This means x=80, y=40, width=240, height=160 inside the `400x240` detection image.

## Printing and Telemetry

Per-frame serial output can dominate the loop and make the screen look slow. Default to LCD overlays for real-time status.

Use switches:

```python
ENABLE_SERIAL_PRINT = False
PRINT_EVERY_N_FRAMES = 15
```

Only print every `N` frames when enabled.

## Display Layer Tradeoff

For basic overlay examples, prefer:

```text
snapshot -> draw on image -> Display.show_image(...)
```

This is simpler and more reliable for drawing circles, centers, FPS, and debug text.

For extreme frame-rate work, consider `Display.bind_layer(...)` for a video layer plus a separate OSD image. This is more complex and should be used only when the user needs maximum FPS and accepts the extra layer-management code.

## Built-In Template

Use `assets/contest-template/examples/circle_detect.py` as the default starting point for circle detection on the 3.1-inch LCD.
