# 2025 Rectangle Target Patterns

Use this reference for 2025-style e-contest vision tasks that need a K230 camera to find a rectangular target, estimate its center, and send coordinates to an external controller.

Source pattern reviewed: https://github.com/abcDesolate/25-vision-collection

For failures, use `troubleshooting.md`: `#camera-problems`, `#lcd-or-display-problems`, `#gpio-pwm-uart-i2c-spi-problems`, and `#contest-integration-problems`.

## Contents

- Strategy Ladder
- Classical Rectangle Tracker
- Optional cv_lite Rectangle Path
- Model-Assisted ROI
- UART Output
- What Not To Copy Directly
- Built-In Template

## Strategy Ladder

Prefer this order during contest bring-up:

1. Start with `assets/contest-template/examples/rectangle_detect.py` to prove camera, LCD, and `find_rects`.
2. Use ROI, grayscale/gamma/binary preprocessing, area filtering, aspect-ratio filtering, and diagonal-intersection center calculation.
3. Add temporal target tracking so the selected rectangle does not jump between false positives.
4. If the firmware provides `cv_lite`, test it as an optional rectangle-corner path after a small `import cv_lite` probe.
5. If the background is too noisy, use a small single-class detector only to propose an ROI, then run classical rectangle/feature detection inside that ROI.
6. Enable UART output only after on-screen target position is stable.
7. Enable gimbal or motor output only after the same on-screen rectangle is confirmed through a vision-only candidate-labeling run.

## Classical Rectangle Tracker

Useful pattern:

- Capture RGB565 at `800x480` for the 3.1-inch LCD.
- Convert a copy to grayscale.
- Apply `gamma_corr(...)` when the black/white contrast needs strengthening.
- Apply `binary([(low, high)], roi=(x, y, w, h))` to restrict the search region.
- Run `find_rects(threshold=...)`.
- Reject candidates outside ROI, below minimum area, or outside aspect-ratio limits.
- Compute the center from the intersection of the two diagonals formed by four corners.
- When multiple candidates exist, choose the largest target at first, then choose the candidate closest to the previous target center.

Do not rely only on `rect.rect()` center for perspective views. It is useful as a fallback, but the corner diagonal intersection is usually better for target aiming.

## Optional cv_lite Rectangle Path

A reviewed K230 rectangle sample used `cv_lite.rgb888_find_rectangles_with_corners(...)` on an RGB888 camera frame to return corner points directly. Treat this as an optional acceleration/accuracy path, not as a baseline dependency.

Useful shape:

```text
RGB888 frame -> cv_lite rectangle candidates -> largest/most stable rectangle -> geometry checks -> diagonal-intersection center -> UART/control
```

Keep these guards when adapting it:

- First run a tiny `import cv_lite` probe on the target firmware; fall back to `image.find_rects(...)` when unavailable.
- Keep the LCD surface full-screen at `800x480`, even if detection runs at `480x320`, `400x240`, or another lower resolution.
- Explicitly scale and rotate candidate corners into LCD coordinates before drawing or sending UART values.
- Filter candidates by area, side-length consistency, parallel/perpendicular angle checks, and center stability.
- Convert desktop-style f-strings, `.format(...)`, comprehensions, and complex inline calls to conservative CanMV MicroPython syntax before final `main.py` delivery.

Board-tested result on the user's Lushan Pi K230 firmware:

- `cv_lite` imported successfully, and `rgb888_find_rectangles_with_corners` existed.
- Official examples were present under `/sdcard/examples/23-CV_Lite/`, including RGB888 and grayscale rectangle-corner demos.
- A bounded RGB888 test using `480x320` detection plus full-screen `800x480` LCD display ran 120 frames without crashing and stabilized around 58-59 FPS.
- With no intentional rectangle target, detections were sparse; tune Canny thresholds, area ratio, and angle cosine on the real contest target before using it for control.
- With a real black-tape rectangle on white paper centered in view, a 300-frame comparison showed:
  - `cv_lite.grayscale_find_rectangles_with_corners`: 299/300 hits, final FPS about 58, average LCD center `(418,214)`, x range `418..418`, y range `210..216`.
  - `cv_lite.rgb888_find_rectangles_with_corners`: 297/300 hits, final FPS about 59, average LCD center `(418,215)`, x range `418..418`, y range `210..216`.
  - Traditional `image.find_rects` after black-threshold binary: 297/300 hits but selected false rectangles repeatedly, final FPS about 22-23, center range `43..420`/`42..262`.
  - Black-threshold `find_blobs`: 300/300 hits and final FPS about 46, but the blob center `(395,279)` was biased away from the rectangle-corner center, so use it only as coarse fallback.
- For black-on-white rectangle targets, prefer grayscale `cv_lite` corners as the first high-FPS tracker. Use RGB888 `cv_lite` when grayscale preprocessing loses useful color contrast. Keep `find_blobs` as a coarse fallback and avoid traditional `find_rects` as the primary path unless extra ROI/geometry filters are added.
- With the user moving, tilting, and changing distance of the same rectangle target during a 600-frame run, strict grayscale `cv_lite` corners reached 503/600 hits at about 59 FPS with no large target jumps (`max_step=26`, `big_jumps=0`). Adding a second relaxed pass only when strict detection returned no rectangles improved continuity to 578/600 hits, with 565 strict hits, 13 fallback hits, 22 misses, about 58 FPS, `max_step=13`, and no large jumps.
- For moving rectangle targets, select candidates using the previous target center while the target has not been lost for too many frames. Use strict parameters first, then a relaxed fallback such as lower Canny thresholds, smaller area ratio, larger polygon epsilon, and larger angle cosine only on missed frames.
- With a black-tape rectangle target on paper that also contained several small rectangles, the normal grayscale `cv_lite` tracker hit 299/300 frames at about 63-64 FPS; the small rectangles were rejected before candidate selection (`max_rects=1`, `big_jumps=0`, center range `446..449`/`180..183`). A deliberately relaxed stress probe reached up to six raw rectangle candidates and five valid candidates, still selected the max-area target on all hit frames, and held 177/180 hits with `big_jumps=0`, center range `445..449`/`180..183`, and about 56-62 FPS. This supports keeping area-first plus previous-center scoring for cluttered paper targets.
- In a 1800-frame lighting robustness test with four 450-frame phases, the same strict-plus-relaxed-fallback tracker stayed stable at about 59 FPS:
  - Normal light: 449/450 hits, all strict, one startup miss, center range `501..505`/`199..204`.
  - Bright light: 450/450 hits, 440 strict and 10 fallback, center range `501..505`/`199..204`.
  - Shadow: 450/450 hits, 443 strict and 7 fallback, center range `501..505`/`199..205`.
  - Dim light: 449/450 hits, 436 strict and 13 fallback, one miss, center range `501..505`/`199..204`.
- For contest lighting changes, keep the fallback pass enabled even if the normal-light strict pass looks perfect. The fallback pass costs little when only run on strict misses and helps absorb exposure/contrast changes without target jumps.

Board-tested ZDT gimbal integration notes:

- Do not use a simple black `find_blobs` target as the actuator input in scenes that contain a computer screen or other large dark objects. A blob-based smoke test can prove the motor chain, but it can chase the wrong object.
- Use `cv_lite` rectangle candidates for black-rectangle gimbal tracking. Confirm the displayed `#1` candidate is the intended paper target before sending any motor command.
- In a cluttered scene with several small black objects, candidate labeling showed the main rectangle as `#1` with area about `20467`; a small dark object appeared as `#2` with area about `630`, so area-first plus geometry filtering selected the correct target.
- A 300-frame cluttered-scene probe reached `298/300` hits, `big_jumps=0`, and about `63 FPS`.
- During active two-axis ZDT tracking with clutter, the tested loop kept `120/120` hits and `15/15` motion ACKs with no target jump.
- Lost-target safety was board-tested: after the rectangle was removed, the loop sent ZDT stop after `3` consecutive missed frames and suppressed later tracking commands.
- Four-direction short tests showed correct convergence directions for a mounted camera: left, right, above, and below targets all moved toward the LCD center under bounded ZDT `FC` control.
- A long fixed/slow target closed-loop run reached `3597/3600` hits, `big_jumps=0`, and `54/54` motion ACKs.
- A full tracking run with the short-test cumulative angle limiter disabled reached `7089/7200` hits at about `50 FPS`, with `486/490` motion ACKs and one large target jump. The target-loss stop fired after `3` consecutive misses, proving the safety path, but also showing that a final competition program should include reacquisition if continued operation is required.

Recommended vision-to-gimbal gate:

```text
PRECHECK:
  run cv_lite rectangle detection only
  require enough hits, stable center, and displayed target confirmation

TRACK:
  send bounded signed pixel-error control to the gimbal
  clamp per-step and total axis motion

LOST:
  after a small number of consecutive misses, send motor stop immediately
  do not continue using the last known target center

REACQUIRE:
  if continuous operation is needed, keep motors stopped
  require the rectangle to be stable again before returning to TRACK
```

## Model-Assisted ROI

The reviewed project includes a one-class `AnchorBaseDet` KModel path generated for K230 with nncase 2.9.0. It uses `nncase_runtime`, `aicube`, and `deploy_config.json`, then calls `aicube.anchorbasedet_post_process(...)`.

Observed model properties:

- `model_type`: `AnchorBaseDet`
- `chip_type`: `k230`
- `nncase_version`: `2.9.0`
- `img_size`: `[640, 640]`
- `num_classes`: `1`
- `categories`: `["1"]`
- `confidence_threshold`: `0.5`
- `nms_threshold`: `0.5`

Use this as an architecture pattern, not as a universal model:

```text
single-class detector -> coarse box/ROI -> classical rectangle corners -> center -> UART/control
```

This is often better than pure YOLO for fixed contest targets, because the model only needs to suppress scene interference while geometry code computes the precise target center.

## UART Output

For target center output, keep the first version simple and readable:

```text
t,<x>,<y>\n
```

For centering control, it is often better to send signed pixel error from image center instead of absolute LCD coordinates:

```text
e,<err_x>,<err_y>\n
```

A reviewed MSPM0 pan/tilt project used a compact bracketed packet style that is useful when the external controller expects fixed-width signed errors:

```text
[+012-034*]
```

In that form the payload is four characters of signed `x` error followed by four characters of signed `y` error, framed by `[` and `*]`. If this format is used, define one consistent lost-target packet such as `[+999+999*]` or a separate `[LOST*]` state; do not mix readable debug strings with controller packets.

Use UART2 only when it matches the user's wiring. The common Lushan Pi examples map:

- `GPIO11 -> FPIOA.UART2_TXD`
- `GPIO12 -> FPIOA.UART2_RXD`
- baud rate `115200`

For final contest control, consider adding a header, sequence id, checksum, or timeout acknowledgment on the external MCU side.

## What Not To Copy Directly

- Do not hard-code third-party model paths such as `/sdcard/mp_deployment_source/` unless the user uses that deployment layout.
- Do not assume the reviewed model files match the user's target or firmware.
- Do not assume `cv_lite` exists on every CanMV firmware image; probe it before writing a final dependency.
- Do not copy `.rknn`, `rknn.api`, OpenCV/Linux camera code, or RK3576 runtime code into a K230 CanMV script.
- Do not keep a low-resolution camera frame centered on the `800x480` LCD without scaling; that causes the "small image in the middle" display failure.
- Do not mix success and failure UART packet formats.
- Do not assume `GPIO53` is the user's button pin.
- Do not preserve temporary debug comments, Chinese mojibake, or unused imports from external examples.
- Do not enable actuators from model output until the same coordinates are stable on LCD and serial logs.
- Do not promote a black-blob smoke test to final gimbal control when the field may include screens, dark backgrounds, cables, or other dark objects.

## Built-In Template

Use `assets/contest-template/examples/cvlite_rectangle_target_uart_tracker.py` first for black-on-white rectangle targets on firmware where `cv_lite` is available. It encodes the board-tested strict-plus-relaxed-fallback `cv_lite` corner strategy, previous-center candidate selection, full-screen LCD overlay, and UART signed-error output.

Use `assets/contest-template/examples/rectangle_target_uart_tracker.py` when `cv_lite` is unavailable or the user needs the older `image.find_rects` route.

Use the simpler `assets/contest-template/examples/rectangle_detect.py` for the first camera/LCD smoke test.

## Acceptance Probe

For a black-tape rectangle target, run:

```powershell
.\tools\test.ps1 -Board -Vision rect-target -Port COM14
```

`ACCEPT_RECT status=pass` means the 300-frame probe saw high hit rate, acceptable FPS, and no concerning center jumps under the current placement. `warn` usually means the target is partially out of ROI, too small/large, lighting changed, or false rectangles are competing. `fail` means do not enable control output from this result.
