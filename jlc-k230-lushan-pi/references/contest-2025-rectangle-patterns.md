# 2025 Rectangle Target Patterns

Use this reference for 2025-style e-contest vision tasks that need a K230 camera to find a rectangular target, estimate its center, and send coordinates to an external controller.

Source pattern reviewed: https://github.com/abcDesolate/25-vision-collection

For failures, use `troubleshooting.md`: `#camera-problems`, `#lcd-or-display-problems`, `#gpio-pwm-uart-i2c-spi-problems`, and `#contest-integration-problems`.

## Contents

- Strategy Ladder
- Classical Rectangle Tracker
- Model-Assisted ROI
- UART Output
- What Not To Copy Directly
- Built-In Template

## Strategy Ladder

Prefer this order during contest bring-up:

1. Start with `assets/contest-template/examples/rectangle_detect.py` to prove camera, LCD, and `find_rects`.
2. Use ROI, grayscale/gamma/binary preprocessing, area filtering, aspect-ratio filtering, and diagonal-intersection center calculation.
3. Add temporal target tracking so the selected rectangle does not jump between false positives.
4. If the background is too noisy, use a small single-class detector only to propose an ROI, then run classical rectangle/feature detection inside that ROI.
5. Enable UART output only after on-screen target position is stable.

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

Use UART2 only when it matches the user's wiring. The common Lushan Pi examples map:

- `GPIO11 -> FPIOA.UART2_TXD`
- `GPIO12 -> FPIOA.UART2_RXD`
- baud rate `115200`

For final contest control, consider adding a header, sequence id, checksum, or timeout acknowledgment on the external MCU side.

## What Not To Copy Directly

- Do not hard-code third-party model paths such as `/sdcard/mp_deployment_source/` unless the user uses that deployment layout.
- Do not assume the reviewed model files match the user's target or firmware.
- Do not assume `GPIO53` is the user's button pin.
- Do not preserve temporary debug comments, Chinese mojibake, or unused imports from external examples.
- Do not enable actuators from model output until the same coordinates are stable on LCD and serial logs.

## Built-In Template

Use `assets/contest-template/examples/rectangle_target_uart_tracker.py` when the user asks for a contest-ready rectangle center detector or laser-target/motor-controller coordinate sender.

Use the simpler `assets/contest-template/examples/rectangle_detect.py` for the first camera/LCD smoke test.
