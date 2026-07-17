# 2025 Rectangle Target Patterns

Use this reference for K230 vision tasks that find a rectangular target, estimate its center, and publish an actuator-neutral target observation.

For failures, use `references/platform/troubleshooting.md`: camera, LCD, probe-result, and contest-integration sections.

## Scope

Use this reference for black-tape rectangle targets, `cv_lite` corners, model-assisted ROI, center tracking, and UART coordinate output. Motor-specific packets and actuator tuning belong only in the confirmed actuator reference.

## Contents

- Strategy Ladder
- Classical Rectangle Tracker
- cv_lite Rectangle Path
- Fast Grayscale Detector
- Model-Assisted ROI
- Temporal Selection
- Control Output Boundary
- UART Output
- Templates and Acceptance

## Strategy Ladder

Use the smallest pipeline that rejects the actual field background:

1. Prove camera and full-screen LCD with `rectangle_detect.py`.
2. Try grayscale `cv_lite` corners for a clean black-on-white target.
3. Add geometry, area, and temporal consistency filters.
4. Add strict-first, relaxed-on-miss detection for lighting changes.
5. If clutter still wins, use a single-class model only to propose an ROI, then refine the rectangle inside it.
6. Stabilize the overlay and coordinate stream before enabling any actuator.

## Classical Rectangle Tracker

Use `image.find_rects(...)` as the compatibility path when `cv_lite` is unavailable:

- capture a display frame suitable for the 3.1-inch LCD;
- process a lower-resolution grayscale copy;
- use ROI, gamma/binary preprocessing, minimum area, and aspect-ratio filters;
- obtain all four corners and calculate the aim point from corner geometry;
- select by area on first lock, then by distance and shape consistency relative to the previous target;
- scale detection coordinates explicitly into the `800x480` display space.

Do not rely on the bounding-box center alone for a perspective target. The four-corner average is stable for tracking; diagonal intersection is useful only when the geometry and corner order have been verified.

## cv_lite Rectangle Path

Probe `import cv_lite` before making it a final dependency. A useful pipeline is:

```text
camera frame
  -> strict cv_lite rectangle corners
  -> relaxed pass only when strict misses
  -> geometry and area gates
  -> temporal candidate selection
  -> four-corner center
```

Keep these invariants:

- `cv_lite.grayscale_find_rectangles_with_corners(...)` is the preferred high-FPS path for high-contrast black tape on white material.
- RGB888 `cv_lite` is a fallback when color contrast carries useful information.
- `find_blobs` is only a coarse fallback because a filled-region center can be biased from the rectangle-corner center.
- Full-frame `find_rects` is not the primary high-FPS route unless ROI and geometry filters are strong.
- Run the relaxed detector only after a strict miss; always reapply the same final area and geometry gates.
- Convert desktop-only syntax to conservative CanMV MicroPython before deployment.

Board-tested conclusions on the reference firmware:

- grayscale `cv_lite` remained stable near 58-64 FPS in clean, moving, cluttered, and changed-lighting target tests;
- strict-first plus relaxed-on-miss improved continuity without introducing large target jumps;
- area-first lock followed by previous-center scoring rejected smaller competing rectangles;
- traditional `find_rects` was slower and more false-positive-prone, while `find_blobs` was useful only for coarse localization.

Exact historical telemetry belongs in the repository `docs/BOARD_TEST_LOG.md`, not in this task reference.

## Fast Grayscale Detector

For a clean target, the low-latency shape is:

```text
Sensor grayscale 640x480
  -> cv_lite grayscale corners
  -> area and geometry gates
  -> corner center
  -> display/observation output
```

Practical starting points, which still require field tuning:

- Canny thresholds around `50/150`;
- polygon epsilon around `0.04`;
- area ratio around `0.001`;
- maximum angle cosine around `0.3`;
- blur size around `5`;
- a real target area floor, rather than accepting every rectangle.

If a `640x480` frame is shown unscaled on the `800x480` LCD, account for the horizontal display offset in overlays. Keep detection, display, and output coordinate spaces explicitly named.

## Model-Assisted ROI

When geometry alone cannot distinguish the intended target, use a detector as a coarse semantic gate:

```text
single-class model box
  -> expand and clip ROI
  -> strict/relaxed cv_lite corners inside ROI
  -> refined center
  -> observation output
```

The model does not need to provide the final aiming center. It should suppress background candidates, while corner geometry supplies the precise center. Before using a custom `.kmodel`, read `references/vision/model-vision-pipeline.md` and the relevant YOLO or AnchorBaseDet API reference.

If refinement misses briefly, hold the last refined center for only one or two frames. A model-box-center fallback should be labeled as coarse, use lower confidence in downstream control, and never masquerade as a refined center.

## Temporal Selection

Maintain a small target state containing:

- center, width, height, area, and four corners;
- detection mode and confidence/quality;
- frame sequence or timestamp;
- consecutive hit and miss counts.

On first acquisition, prefer the largest geometrically valid candidate. While locked, score candidates by distance from the previous center plus width, height, and area change. Clear the lock after bounded misses and require consecutive valid hits before reporting reacquisition.

Draw the raw candidate and stabilized output center separately while tuning. This exposes candidate switches without allowing a one-frame jump to propagate into control.

## Control Output Boundary

This reference ends at an actuator-neutral observation:

```text
target_valid, center_x, center_y, error_x, error_y,
quality, mode, sequence, timestamp
```

The vision layer may apply bounded center filtering and mark data stale, but it must not invent motor frames, axis signs, holding behavior, or mechanical limits. Route confirmed ZDT hardware to `references/control/zdt-stepper-gimbal-patterns.md`; route other actuators to their own protocol reference. If the actuator is unknown, output coordinates only.

## UART Output

Readable bring-up format:

```text
t,<x>,<y>\n
```

Signed center-error format:

```text
e,<err_x>,<err_y>\n
```

For a fixed packet, define framing, sequence, checksum, stale timeout, and one unambiguous lost-target state. Do not mix human debug text with controller packets on the same channel unless the receiver explicitly supports it.

Use UART2 only after the pin pair is confirmed with `references/platform/hardware-pin-resource-quickref.md` or `scripts/run_board_probe.py --vision uart-loopback`.

## Templates and Acceptance

Use these templates in order:

- `assets/contest-template/examples/vision/rectangle_detect.py` for first camera/LCD proof;
- `assets/contest-template/examples/control/cvlite_rectangle_target_uart_tracker.py` for the preferred `cv_lite` path;
- `assets/contest-template/examples/control/rectangle_target_uart_tracker.py` for the compatibility path.

From the folder containing `SKILL.md`, run the RAM-only target probe:

```powershell
python .\scripts\run_board_probe.py --vision rect-target --port COM14
```

`ACCEPT_RECT status=pass` means the bounded probe met its hit-rate, FPS, and center-jump gates in the current scene. For `warn` or `fail`, follow `references/platform/troubleshooting.md#probe-result-actions`; do not enable actuator output from an unaccepted observation stream.
