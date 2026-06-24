# Electronic Design Contest Patterns

For integration failures, use `troubleshooting.md#contest-integration-problems`. For scope limits such as actuator safety, unsupported boards, or uncertain pins, use `sources-and-boundaries.md#applicability-boundaries`.

## Contents

- Default Architecture
- Competition Priorities
- Runtime Resilience
- Field Mode Acceptance
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
- `assets/contest-template/examples/cvlite_rectangle_target_uart_tracker.py`: high-FPS black-on-white rectangle tracker using `cv_lite` grayscale corners, strict-plus-relaxed fallback detection, previous-center target selection, LCD overlay, and UART signed-error output.
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

When the template changes because of firmware or API updates, record the reason in `maintenance.md#maintenance-summary`; put long chronological test history in repository-level `docs/BOARD_TEST_LOG.md` when available.

## Competition Priorities

- Prefer stable frame rate and explainable thresholds over maximum visual complexity.
- Add a debug overlay for target center, confidence, state, and actuator command. Serial prints should be switch-controlled or throttled every `N` frames.
- Keep fallback modes: no target, low confidence, UART timeout, motor stop, and model load failure.
- Put all thresholds and pin mappings at the top of the file.
- Keep data flow deterministic: camera frame -> result -> decision -> output.
- Use simple state machines for tasks such as tracking, sorting, line following, target locking, and timed actions.

## Runtime Resilience

Contest code should fail safe before it fails loud. For any integrated `main.py` that owns actuators or communicates with an external controller, include a bounded runtime recovery pattern instead of a single top-level `try/finally`.

Required states:

- `BOOT`: show startup status, initialize outputs to neutral.
- `READY`: camera/display/model/peripherals initialized.
- `TRACK`: perception is valid and control output is enabled.
- `SEARCH`: perception is temporarily missing; output should be neutral, slow, or scan-limited.
- `LOST`: target timeout exceeded; send a single consistent lost-target packet.
- `RECOVER`: frame/model/display error occurred; stop outputs, attempt bounded recovery.
- `FAULT`: recovery budget exceeded; hold neutral output and show the failure reason.

Use small counters and timeouts:

- `target_miss_count`: consecutive frames without a valid target.
- `frame_error_count`: consecutive `sensor.snapshot()`, `pl.get_frame()`, model, or drawing failures.
- `recover_count`: number of pipeline restart attempts since boot.
- `last_target_ms`: timestamp of the last valid target.
- `uart_rx_deadline_ms`: timeout for external MCU acknowledgments if used.

Useful inline shape for final CanMV code:

```python
def safe_stop_outputs(reason):
    # 比赛中任何异常都先让输出回到安全状态
    set_pwm_output(PWM_NEUTRAL_DUTY_U16)
    if uart is not None:
        uart.write("STATE:SAFE_STOP,REASON:%s\r\n" % reason)


def handle_frame_error(reason):
    global frame_error_count
    frame_error_count += 1
    safe_stop_outputs(reason)
    if frame_error_count >= RUNTIME_ERROR_LIMIT:
        recover_camera_or_raise(reason)
```

For raw `Sensor`/`Display` preview code, a bounded recovery attempt can stop the sensor, deinitialize `Display` and `MediaManager`, collect garbage, sleep briefly, then re-run the same camera/LCD init path. Use `assets/contest-template/main.py` as the integrated example.

Board-tested recovery result on the user's Lushan Pi K230: an injected raw preview recovery through raw REPL on COM14 showed 10 frames before recovery, then successfully ran `Sensor.stop()`, `Display.deinit()`, `MediaManager.deinit()`, reinitialized the default `gc2093_csi2` camera plus 3.1-inch `Display.ST7701` LCD, showed 10 more frames, and exited cleanly with one recovery.

For YOLO/PipeLine code, prefer safe stop plus visible fault state after repeated frame/model exceptions unless the exact `PipeLine.destroy()` and recreate path has been board-tested. Recreating AI pipelines repeatedly can leak resources or fragment memory on embedded firmware, so do not promise live model recovery without a real board test.

Do not hide persistent faults. After the recovery budget is exceeded, keep actuators neutral, show `FAULT` on LCD, and continue sending a simple fault/lost packet if the UART path still works.

## Field Mode Acceptance

Before turning a tested probe into a competition `main.py`, require a field-mode pass:

1. The program starts automatically after reset or power cycle when named `/sdcard/main.py`.
2. LCD shows a compact status page or overlay with `BOOT`, `READY`, `TRACK`, `SEARCH`, `LOST`, `RECOVER`, or `FAULT`.
3. The overlay shows FPS, target center or signed error, confidence/area/radius, active threshold/preset, and UART/control state.
4. A no-PC adjustment path exists for light-sensitive vision: button-selected preset, Otsu calibration, or conservative fallback thresholds.
5. UART output has one normal packet and one lost/fault packet; debug text does not share the same controller stream unless the receiver expects it.
6. Actuators remain disabled or neutral until LCD overlay and UART logs are stable.
7. Consecutive frame errors enter `RECOVER`; repeated recovery failure enters visible `FAULT`.
8. The last check is a full reset or power cycle, not only the IDE green-run button.

Use `tools/test.ps1` for the pre-integration probes:

- Rectangle target: `.\tools\test.ps1 -Board -Vision rect-target -Port COM14`; continue only after `ACCEPT_RECT status=pass` or a deliberate explanation for `warn`.
- Circle target: `.\tools\test.ps1 -Board -Vision circle-target -Port COM14`; treat `warn` as a tuning prompt because circle detection is target-dependent.
- YOLO: `.\tools\test.ps1 -Board -Vision yolo -Port COM14`; continue only if the runtime imports pass and the expected `.kmodel` path is known.
- UART: `.\tools\test.ps1 -Board -Vision uart-loopback -Port COM14`; continue only after wiring is verified by loopback or by the external MCU observer.

## Vision Tasks

For color/shape/line tasks, start with classical image processing before YOLO:

- ROI crop to reduce processing.
- Threshold in LAB/RGB/gray depending on lighting.
- For competition-site lighting drift, prefer calibration or dynamic thresholds over one fixed value: compute min/max, a histogram, or local ROI statistics, then derive the threshold per frame or per calibration step.
- Use blob/line/circle detection where adequate.
- Display tuning values on LCD by default. Avoid per-frame `print(...)` in real-time vision loops because serial output can dominate frame time.
- Save fallback threshold presets for the competition site lighting, and make the active preset visible on LCD.

For 2025-style rectangle target or laser aiming tasks, read `contest-2025-rectangle-patterns.md` before writing final code. Prefer `cvlite_rectangle_target_uart_tracker.py` when `cv_lite` is available; use the `find_rects` tracker as a fallback route.

For circle/ring detection, read `circle-detection-patterns.md`. Prefer full-screen `800x480` display with `400x240` or `320x240` detection, ROI, coordinate scaling, and detection every `N` frames.

For any ready-to-copy `main.py`, read `canmv-api-known-issues.md#conservative-syntax-and-validation` and use conservative CanMV MicroPython syntax.

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

For K230 plus MSPM0/MSPM0G-style dual-core contest systems:

- Treat K230 as the vision processor and the MCU as the motion/control processor.
- Keep K230 output limited to target state: found/lost, signed error, center, radius/area, confidence, or phase.
- Put motor/servo PID, limit switches, emergency stop, and actuator safety on the MCU side whenever possible.
- Start with a human-readable packet such as `e,<err_x>,<err_y>\n`, then move to a fixed binary frame only after wiring and direction are verified.
- For Wheeltec-compatible bring-up, a common 8-byte test shape is `FF FE pan tilt 00 00 00 BCC`, where `BCC` is the XOR of bytes 0 through 6. Use it only when the receiver expects that frame family.
- Verify common ground and baud rate before tuning vision. Some public dual-chip examples used 9600 baud for bring-up even when 115200 was used elsewhere.
- Use `scripts/probe_uart2_loopback.py` to identify the K230 TX pad before blaming the MCU parser.

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
