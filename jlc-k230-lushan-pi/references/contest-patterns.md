# Electronic Design Contest Patterns

For integration failures, use `troubleshooting.md#contest-integration-problems`. For scope limits such as actuator safety, unsupported boards, or uncertain pins, use `usage-boundaries.md`.

## Contents

- Default Architecture
- Competition Priorities
- Vision Tasks
- Actuation and Communication
- Debugging
- Response Style

## Default Architecture

Use `assets/contest-template/` as the copyable starting point for a new project. Its shape is:

```text
main.py
  config constants
  init_hardware()
  read_inputs()
  perception_step()
  decision_step()
  actuation_step()
  telemetry_step()
  cleanup()

examples/
  camera_lcd_preview.py
  uart2_loopback.py
  pwm_buzzer_smoke.py
  button_capture.py
```

Use the `examples/` files to verify each hardware block before integrating the contest task in `main.py`.

Current template files:

- `assets/contest-template/main.py`: integrated contest scaffold. It runs camera-to-LCD preview by default and has optional UART, PWM safe output, and YOLO video pipeline switches.
- `assets/contest-template/boot.py`: minimal boot file that does not block `main.py`.
- `assets/contest-template/examples/camera_lcd_preview.py`: first smoke test for camera + 3.1-inch LCD.
- `assets/contest-template/examples/uart2_loopback.py`: UART2 communication smoke test.
- `assets/contest-template/examples/pwm_buzzer_smoke.py`: PWM/buzzer smoke test.
- `assets/contest-template/examples/button_capture.py`: button-triggered image capture template for dataset collection.
- `assets/contest-template/examples/yolov8_lcd_official_launcher.py`: board-proven launcher for the official YOLOv8 object detection example on the 3.1-inch LCD.
- `assets/contest-template/examples/rectangle_detect.py`: board-tested classical rectangle detection and annotation example using `find_rects`.
- `assets/contest-template/examples/rectangle_target_uart_tracker.py`: contest-style rectangle center tracker with ROI, binary preprocessing, diagonal-intersection center, temporal target selection, and UART output.
- `assets/contest-template/examples/circle_detect.py`: full-screen LCD circle detection template using low-resolution detection, scaled overlay coordinates, ROI, throttled detection, and throttled serial print.
- `assets/contest-template/examples/color_line_tracking.py`: color blob and line segment tracking pattern.
- `assets/contest-template/examples/servo_laser_stepper_patterns.py`: laser GPIO, servo PWM, stepper phase-table, and button mode pattern.
- `assets/contest-template/examples/offline_threshold_tuner.py`: button-based LAB threshold tuner for offline contest use.
- `assets/contest-template/examples/pid_target_centering.py`: PID and UART packet helpers for target-centering control.

When creating a new contest project:

1. Copy `assets/contest-template/` to the user's project folder.
2. Run `examples/camera_lcd_preview.py` first.
3. Run only the hardware-specific smoke tests needed by the project.
4. Edit top-level constants in `main.py`.
5. Enable optional blocks such as `USE_YOLO`, `ENABLE_UART`, or `ENABLE_PWM_SAFE_OUTPUT`.
6. Save the final integrated program as `main.py` for offline deployment.

When the template changes because of firmware or API updates, record the reason in `maintenance.md#revision-log`.

## Competition Priorities

- Prefer stable frame rate and explainable thresholds over maximum visual complexity.
- Add a debug overlay for target center, confidence, state, and actuator command. Serial prints should be switch-controlled or throttled every `N` frames.
- Keep fallback modes: no target, low confidence, UART timeout, motor stop, and model load failure.
- Put all thresholds and pin mappings at the top of the file.
- Keep data flow deterministic: camera frame -> result -> decision -> output.
- Use simple state machines for tasks such as tracking, sorting, line following, target locking, and timed actions.

## Vision Tasks

For color/shape/line tasks, start with classical image processing before YOLO:

- ROI crop to reduce processing.
- Threshold in LAB/RGB/gray depending on lighting.
- For competition-site lighting drift, prefer calibration or dynamic thresholds over one fixed value: compute min/max, a histogram, or local ROI statistics, then derive the threshold per frame or per calibration step.
- Use blob/line/circle detection where adequate.
- Display tuning values on LCD by default. Avoid per-frame `print(...)` in real-time vision loops because serial output can dominate frame time.
- Save fallback threshold presets for the competition site lighting, and make the active preset visible on LCD.

For 2025-style rectangle target or laser aiming tasks, read `contest-2025-rectangle-patterns.md` before writing final code. Prefer the enhanced tracker template when the user needs stable center coordinates over UART.

For circle/ring detection, read `circle-detection-patterns.md`. Prefer full-screen `800x480` display with `400x240` or `320x240` detection, ROI, coordinate scaling, and detection every `N` frames.

For any ready-to-copy `main.py`, read `canmv-micropython-compatibility.md` and use conservative CanMV MicroPython syntax.

For YOLO/model tasks:

- Verify the `.kmodel` loads before connecting actuators.
- Run still-image inference first if possible.
- Then run camera inference without control outputs.
- Only then enable actuation.

## Actuation and Communication

For UART-connected motor controllers or MCUs:

- Define a packet format with header, payload, checksum or newline.
- For target-centering controllers, send signed pixel error or normalized error when the MCU closes the loop; absolute coordinates are mainly for logging and display.
- Use one success format and one lost-target/timeout format; avoid mixing debug strings and controller packets on the same UART stream.
- Add timeout handling.
- Echo or log received responses during bring-up.

For PWM/servo/motor outputs:

- Clamp outputs.
- Provide a neutral/stop command in every exception path.
- Test manually with small duty changes before adding vision feedback.

## Debugging

Use `troubleshooting.md` for failure diagnosis. Keep this file focused on the intended contest architecture and normal development flow.

## Response Style

When helping the user during a contest build, answer with:

- a shortest reliable bring-up plan
- the exact file(s) or script(s) to run
- one minimal runnable code block when code is requested
- a checklist of what to observe on screen/serial output
- next diagnosis steps if the result differs
