# CanMV Workflows

## Project Bring-Up

For a new contest project, start with one verified subsystem at a time:

1. Boot board and connect CanMV IDE K230.
2. Run a minimal print/LED/GPIO test.
3. Run camera preview to IDE virtual display.
4. Run LCD display on the 3.1-inch screen.
5. Add the target peripheral bus such as UART, PWM, I2C, or SPI.
6. Add image processing or model inference.
7. Add control output and telemetry.

Prefer keeping an `examples/` directory with known-good single-feature scripts and a `main.py` that integrates them.

On Windows, CanMV IDE K230 may be installed in a user-chosen directory. When the user asks to launch, locate, or troubleshoot the IDE, first ask for or discover the path to `canmvide.exe` instead of assuming a fixed drive path.

When CanMV IDE UI automation is unavailable, try running a temporary script through K230 MicroPython raw REPL with `scripts/run_canmv_raw_repl.py`. The user's tested board exposed a USB serial port with `VID:PID=1209:ABD1`, but that ID is a tested auto-detection hint rather than a universal K230 guarantee; pass `--port COMx` whenever auto-detection is uncertain. The helper tries baud `2000000` and then `115200` when `--baud` is omitted. This method runs code from RAM and does not save `main.py` to the TF card.

When the user explicitly asks to deploy files to `/sdcard`, pull a runtime snapshot, or iterate with `mpremote`, read `mpremote-debug-workflows.md` and use `scripts/mpremote_deploy.py` or `scripts/mpremote_snapshot.py`. Keep this separate from RAM-only raw REPL testing because `mpremote_deploy.py` writes board files.

When hardware is connected and a quick camera/LCD check is needed, run `scripts/smoke_camera_lcd.py` through `scripts/run_canmv_raw_repl.py`. It initializes the default CSI camera and the 3.1-inch `Display.ST7701` LCD, shows 20 frames, prints `SMOKE_DONE`, and exits. Use this before debugging a large application or an infinite-loop template.

When camera identity or constructor behavior is uncertain, run `scripts/probe_k230_sensor_init.py` through `scripts/run_canmv_raw_repl.py`. It tries the Lushan default `Sensor(id=2)`, smaller QVGA modes, default `Sensor()`, and selected alternate ids, then prints which modes can snapshot. Use it before changing final camera code away from the normal `Sensor(id=2)` path.

When black/white threshold calibration needs a board-side check without entering the infinite offline tuner loop, run `scripts/probe_otsu_threshold.py` through `scripts/run_canmv_raw_repl.py`. It samples 30 low-resolution grayscale frames, verifies blob detection, shows a short result screen on the 3.1-inch LCD, and exits.

For user-preferred example style, read `user-example-patterns.md`. It contains distilled patterns from the user's prior working code, without relying on local machine paths.

For failures during bring-up, use `troubleshooting.md#first-pass` first, then the task-specific sections below.

## Contents

- Project Bring-Up
- FPIOA and GPIO
- UART
- PWM
- I2C and SPI
- Camera
- Display and 3.1-Inch LCD
- YOLO and Image Recognition

## FPIOA and GPIO

Use `FPIOA` before each pin/peripheral object:

```python
from machine import FPIOA, Pin

fpioa = FPIOA()
fpioa.set_function(2, FPIOA.GPIO2)
led = Pin(2, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
led.value(1)
```

The official GPIO/FPIOA page states that FPIOA can map pins to functions such as GPIO, UART, IIC/I2C, and PWM, and each pin can only activate one function at a time. Use `fpioa.help(pin)` and `fpioa.help(func, func=True)` to inspect current and possible mappings.

The current official GPIO tutorial notes that CanMV firmware does not support configuring pins as interrupt mode. Prefer polling or timer-based checks unless the user's installed firmware proves otherwise.

If GPIO or FPIOA mapping does not work, use `troubleshooting.md#gpio-pwm-uart-i2c-spi-problems`.

## UART

Route UART pins with `FPIOA` first, then construct `UART`. Ask for the connected module voltage level, baud rate, TX/RX cross-over, and whether the peripheral needs newline-terminated packets.

Use a small packet parser for contest sensors and motor controllers:

```python
from machine import FPIOA, UART

fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)
uart = UART(UART.UART2, baudrate=115200, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)
uart.write("hello\r\n")
```

Verify pin numbers against the official pin table or user schematic before presenting code as final.

When the user is not sure which UART2 pins are shorted or wired, run `scripts/probe_uart2_loopback.py` through raw REPL. It first scans common UART2 FPIOA pairs `(5, 6)`, `(11, 12)`, and `(44, 45)` as GPIO links, then runs a bounded UART2 loopback test on the linked pair.

If UART data is missing, garbled, or one-way only, use `troubleshooting.md#gpio-pwm-uart-i2c-spi-problems`.

## PWM

Use PWM for servos, buzzers, LEDs, and motor driver inputs only after checking pin multiplexing:

```python
from machine import FPIOA, PWM

fpioa = FPIOA()
fpioa.set_function(42, FPIOA.PWM0)
pwm = PWM(0, freq=50, duty=7.5, enable=True)
```

For servos, expose constants for min/max pulse and clamp outputs. For motor control, separate direction GPIO from speed PWM.

If PWM output does not appear or actuator behavior is unsafe, use `troubleshooting.md#gpio-pwm-uart-i2c-spi-problems`.

## I2C and SPI

The basic I2C tutorial may be unavailable or marked waiting for update, so use the I2C/SPI API manuals and the user's installed firmware. Always ask for module address, required bus speed, and wiring. For SPI displays or sensors, ask for mode, chip select pin, and maximum clock.

If I2C/SPI devices do not respond, use `troubleshooting.md#gpio-pwm-uart-i2c-spi-problems`.

## Camera

Use the Sensor module for camera input. The official camera page says Lushan Pi's default camera interface is CSI2; when `Sensor()` does not specify an id, it is equivalent to `Sensor(id=2)` for the default board camera.

Use `assets/contest-template/examples/camera_lcd_preview.py` as the copyable camera/LCD skeleton. This reference keeps only workflow rules: initialize `Sensor`, `Display`, and `MediaManager` in order; keep display selection as a top-level constant; run `sensor.stop()`, `Display.deinit()`, `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)`, and `MediaManager.deinit()` in cleanup.

Adjust resolution to fit the display, algorithm, and memory budget. For AI inference, a lower sensor/display stream and separate model input size are usually easier to keep real-time. For expensive classical detectors such as `find_circles`, prefer a dual-channel layout: full-screen `800x480` display on one channel and `400x240` or `320x240` detection on another channel, then scale coordinates back to the LCD.

If camera initialization, frame capture, or FPS is wrong, use `troubleshooting.md#camera-problems`.

If the default `Sensor(id=2)` path fails on a new firmware/camera, run `scripts/probe_k230_sensor_init.py` from RAM and use only the successful mode as a temporary workaround. Record the result in `maintenance.md` before changing templates globally.

## Display and 3.1-Inch LCD

For the 3.1-inch MIPI screen, prefer `Display.ST7701`. Keep display mode as a top-level constant so the same script can switch between IDE virtual display, LCD, and HDMI while debugging.

When the user asks for 3.1-inch LCD output, default to full-screen display. If using a lower-resolution processing image, do not accidentally show a small centered image unless that is explicitly a debug view.

For overlay examples, prefer `snapshot -> draw -> Display.show_image(...)`. Consider `Display.bind_layer(...)` plus an OSD layer only for high-FPS video-layer work where the extra complexity is worth it.

If the user reports no backlight, check the screen expansion board connection first: 31P MIPI cable, 6P touch cable, power, and backlight circuit. The expansion board's backlight normally powers on by default because the enable line is pulled up, but brightness control depends on the I2C-to-PWM backlight circuit.

If the LCD is blank, dark, mirrored, or only works in IDE preview, use `troubleshooting.md#lcd-or-display-problems`.

## YOLO and Image Recognition

For YOLO tasks, collect these inputs before writing final code:

- task type: detect, segment, classify, pose, or other supported mode
- `.kmodel` path on the board
- labels list path or inline labels
- model input size
- RGB888 planar/non-planar expectation
- confidence, NMS, and mask thresholds
- display mode and desired overlay behavior

Use the official YOLO module API as the source for class names and constructor arguments. Keep model inference in a function such as `run_detector(img)` and rendering in `draw_result(...)` so the contest control logic can be tested without camera hardware.

If model loading, inference, labels, or result drawing fails, use `troubleshooting.md#yolo-kmodel-or-ai-problems`.
