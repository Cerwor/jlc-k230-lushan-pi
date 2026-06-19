# Built-In Training Example Patterns

This file contains built-in contest-oriented training patterns. Use this reference and the templates under `assets/contest-template/examples/` without depending on any external example folder.

## Contents

- Camera and Drawing
- Rectangle Recognition
- 2025-Style Rectangle Target Tracking
- Circle Recognition
- Color Blob and Line Segment Tracking
- UART Communication
- Laser, Servo, and Stepper Control
- Data Collection and AI Digit Recognition
- Offline Threshold Tuning
- PID Laser Centering and 2023 E Problem Pattern

## Camera and Drawing

Reusable patterns:

- Initialize `Sensor`, `Display`, and `MediaManager` in that order.
- Use `Display.ST7701`, `width=800`, `height=480`, `to_ide=True` for the 3.1-inch LCD.
- Use `draw_string_advanced`, `draw_line`, `draw_rectangle`, `draw_keypoints`, `draw_circle`, `set_pixel`, and `draw_cross` for visual debugging.
- Use visible overlays for FPS, threshold values, selected mode, target center, and control output.

Built-in templates:

- `assets/contest-template/examples/camera_lcd_preview.py`
- `assets/contest-template/examples/rectangle_detect.py`
- `assets/contest-template/examples/circle_detect.py`

## Rectangle Recognition

Original useful pattern:

```python
img_rect = img.to_grayscale(copy=True)
img_rect = img_rect.binary([(82, 212)])
rects = img_rect.find_rects(threshold=10000)
for rect in rects:
    corner = rect.corners()
    img.draw_line(corner[0][0], corner[0][1], corner[1][0], corner[1][1], color=(0, 255, 0), thickness=5)
```

Portable guidance:

- Default to full-screen `800x480` LCD output with a lower-resolution detection channel such as `400x240`; scale corners and center back to LCD coordinates.
- Use grayscale/binary preprocessing when rectangle edges are weak.
- Avoid running `find_rects(threshold=...)` over full `800x480` by default; it can drop to only a few FPS.
- Draw corners and center point, not only the bounding box.
- Tune `RECT_THRESHOLD`, binary threshold, and minimum area at the contest site.

Built-in template:

- `assets/contest-template/examples/rectangle_detect.py`

## 2025-Style Rectangle Target Tracking

Use this pattern when rectangle detection must drive an external controller, laser aiming, or a target-centering loop.

Portable guidance:

- Start from the simple rectangle template, then add ROI, binary preprocessing, area/aspect filters, and temporal target tracking.
- Keep the tracker on the same full-screen display plus lower-resolution detection-channel architecture as the simple rectangle template; full-frame `800x480` preprocessing can run around 8 FPS on the tested board.
- Compute the aim point from the intersection of the two diagonals of the detected corners.
- Send center coordinates only after the overlay is stable on the LCD.
- Use a single-class detector only as a coarse ROI provider when traditional vision sees too many false positives.

Reference and template:

- `references/contest-2025-rectangle-patterns.md`
- `assets/contest-template/examples/rectangle_target_uart_tracker.py`

## Circle Recognition

Use this pattern for round targets, rings, balls, coins, or circular marks.

Portable guidance:

- Default to full-screen `800x480` LCD output on the 3.1-inch screen.
- Run `find_circles` on a lower-resolution detection channel such as `400x240` or `320x240`.
- Keep ROI coordinates in detection-image space, then scale center/radius back to LCD coordinates.
- Tune Hough parameters for the target size and contrast. A bottle-cap live test on the 400x240 detection channel needed `CIRCLE_THRESHOLD = 1200` and `X/Y_STRIDE = 2`; the older `2500`/`4` setting missed it.
- Use `DETECT_EVERY_N_FRAMES`, a short miss-hold window, and keep serial printing disabled or throttled.
- Draw the LCD-coordinate circle and center cross on the full-screen display image.

Reference and template:

- `references/circle-detection-patterns.md`
- `assets/contest-template/examples/circle_detect.py`

## Color Blob and Line Segment Tracking

Original useful patterns:

```python
img_line = img.to_rgb565(copy=True)
img_line.midpoint_pool(2, 2)
lines = img_line.find_line_segments((0, 0, 512, 384), 15, 15)
for line in lines:
    if line.length() > 100:
        img.draw_line(line.x1()*2, line.y1()*2, line.x2()*2, line.y2()*2, color=(0, 255, 0), thickness=5)
```

```python
blobs = img.find_blobs([(41, 57, 31, 83, 13, 71)], False,
                       (0, 0, 640, 640), x_stride=5, y_stride=5,
                       pixels_threshold=3000, margin=True)
for blob in blobs:
    img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(), color=(0, 255, 0), thickness=6)
```

Portable guidance:

- Default to full-screen `800x480` LCD output with a lower-resolution detection channel such as `400x240`.
- Downsample the detection image with `midpoint_pool(2, 2)` for line detection, then scale coordinates back to LCD coordinates.
- Use ROI to reduce false positives and improve FPS.
- Put LAB thresholds at the top of the file.
- For color tasks, output blob center, area, and bounding box.

Built-in template:

- `assets/contest-template/examples/color_line_tracking.py`

## UART Communication

Original useful patterns:

- Map `GPIO11 -> UART2_TXD` and `GPIO12 -> UART2_RXD`.
- Use `UART(UART.UART2, 115200)`.
- Send both text and raw bytes.
- Read with `uart.read()`, then print bytes, decoded text, and byte list when debugging.

Portable guidance:

- Prefer UART2 for external controllers.
- If loopback wiring is uncertain, run `scripts/probe_uart2_loopback.py`; UART2 may be mapped to `PIN5/PIN6`, `PIN11/PIN12`, or `PIN44/PIN45` depending on the connector/pads used.
- Cross TX/RX and share GND.
- Do not assume received bytes are valid UTF-8; catch decode failures.
- For contest control, define a packet format and checksum.

Built-in template:

- `assets/contest-template/examples/uart2_loopback.py`

## Laser, Servo, and Stepper Control

Original useful patterns:

- Laser switch: map a GPIO and toggle `Pin.OUT`.
- Servo: use PWM at 50 Hz, with duty corresponding to roughly 0.5-2.5 ms pulse width.
- Stepper: use four GPIO outputs and a four-state phase table.
- Timer callback can advance the stepper phase periodically.
- Button cycles motor state or mode.

Portable guidance:

- Confirm external driver voltage/current before enabling actuators.
- Clamp servo output.
- Provide neutral/stop commands in `finally`.
- Keep outputs disabled until vision detection is stable.

Built-in templates:

- `assets/contest-template/examples/pwm_buzzer_smoke.py`
- `assets/contest-template/examples/servo_laser_stepper_patterns.py`

## Data Collection and AI Digit Recognition

Original useful patterns:

- Use a button to start/stop capture.
- Save images under `/sdcard/capture` or another known TF-card directory so samples are easy to copy after offline collection.
- Overlay capture state and saved image count.
- For AI digit recognition, keep model path, labels, input size, and preprocessing constants at the top.

Portable guidance:

- Collect data at the contest lighting/site when possible.
- Save filenames with a monotonically increasing index.
- Expect JPEG encoding and TF-card writes to temporarily reduce FPS; keep capture interval throttled.
- Keep collection code separate from inference code.
- For `button_capture.py`, the physical `USR` key was board-tested as `PAD52 -> FPIOA.GPIO53 -> Pin(53)` with pull-down input, idle `0`, pressed `1`; one press toggles capture on, the next press toggles it off.

Built-in template:

- `assets/contest-template/examples/button_capture.py`

## Offline Threshold Tuning

Original useful pattern:

- Use onboard buttons/touch/serial to adjust thresholds when a PC is unavailable.
- Show current threshold values on the LCD.
- Store tuned values as constants before final deployment.

Portable guidance:

- For threshold-heavy tasks, write a tuning script before writing the final autonomous script.
- Default to full-screen `800x480` LCD output with a lower-resolution detection channel such as `400x240`; scale blob boxes and centers back to LCD coordinates.
- Display mode, current selected parameter, and current threshold values must be visible.
- Keep a fallback threshold set for known lighting conditions.
- On the tested board, the template keys `GPIO53/GPIO32/GPIO34` should use pull-ups and active-low edge detection. Initialize debounce state from the current pin values; a `GPIO53` pull-down, active-high NEXT key falsely triggered after camera/LCD startup.

Built-in template:

- `assets/contest-template/examples/offline_threshold_tuner.py`

## PID Laser Centering and 2023 E Problem Pattern

Original useful patterns:

- Use a simple PID/incremental controller around a target pixel center.
- Use repeated calculation or frame confirmation to reject false detections.
- Use UART packets to command an external motor controller.
- For 2023 E-style tasks, split image target extraction, geometry calculation, control output, and state machine.

Portable guidance:

- Keep target center constants at the top.
- Use deadband around the target center to avoid oscillation.
- Disable or clamp actuator output when target confidence is low.
- Log target position and control command on screen and serial.

Built-in template:

- `assets/contest-template/examples/pid_target_centering.py`
