# CanMV API Known Issues

Use this file when K230 CanMV code fails because an API behaves differently from desktop Python, old CanMV examples, or unofficial notes.

This is not a replacement for the official API manual. For unfamiliar classes or function signatures, still route through `sources-and-boundaries.md#api-manual-routing` first.

## Contents

- Scope
- High-Value Pitfalls
- Sensor and Display
- Pins and Peripherals
- Image Processing
- Conservative Syntax And Validation
- Code Generation Checklist
- Source Notes

## Scope

These notes are distilled from this skill's board tests plus a reviewed public MSPM0G/K230 contest repository. The reviewed K230 material targets Lushan Pi K230, GC2093 camera, CanMV MicroPython, and a 3.1-inch ST7701 MIPI screen, so it is relevant to this skill. Treat its version-specific observations as hints, not universal firmware guarantees.

## High-Value Pitfalls

- `FPIOA` must be configured before `Pin`, `UART`, `PWM`, I2C, SPI, or external signal use.
- K230 GPIO/header IO is 3.3 V, but ADC input max is 1.8 V and is not on the normal 40Pin header.
- Use `Timer(-1)` or `ticks_ms` style software timing unless the user's firmware proves hardware timers are exposed.
- Final CanMV code should avoid f-strings, comprehensions, `lambda`, conditional expressions, and heavy inline calls.
- `pin.high()`, `pin.low()`, `pin.on()`, and `pin.off()` are not safe assumptions; use `pin.value(1)` and `pin.value(0)`.
- Some MicroPython stdlib APIs differ from CPython. For example, `hashlib.hexdigest()` may be missing; use `binascii.hexlify(hash.digest())` if hashing is truly needed.
- UART hardware interrupts are not a safe assumption in CanMV MicroPython. Prefer polling with `uart.read()` and a small parser.
- `I2C(1, freq=...)` style bus numbers are safer than assuming enum attributes exist.

## Sensor And Display

- For the user's Lushan Pi K230 with the default GC2093 camera, prefer `Sensor()` or `Sensor(id=2)`. Use `scripts/probe_k230_sensor_init.py` when firmware, CSI port, or camera module is uncertain.
- `Sensor(width=..., height=...)` may work in IDE virtual-display examples but should not replace the board default camera id in final physical-LCD code unless tested.
- Keep initialization order stable: configure `Sensor`, call `Display.init(...)`, then `MediaManager.init()`, then `sensor.run()`.
- Deinitialize in the reverse-safe direction: stop the sensor, deinit `Display`, sleep briefly through `os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)` when available, then deinit `MediaManager`.
- `Display.ST7701`, width `800`, height `480` is the default for the 3.1-inch screen.
- `Display.bind_layer(...)` is version-sensitive. If used, bind before `Display.init(...)` and pass the dictionary returned by `sensor.bind_info()` carefully. Prefer `snapshot -> draw -> Display.show_image(img)` unless high-FPS video-layer behavior is worth the complexity.
- Dual-channel camera setups are firmware-dependent. This skill has board-tested dual-channel templates on the user's firmware, while other CanMV builds have reported `snapshot chn(1)` failures. If dual-channel fails, fall back to single-channel full-screen capture plus ROI/stride/skip-frame detection.
- Do not display a low-resolution image centered on the LCD unless it is explicitly a debug view. For final LCD output, use full-screen `800x480` display and scale lower-resolution detection coordinates back to LCD coordinates.

## Pins And Peripherals

- PWM constructor signatures vary. For contest code, prefer simple construction plus setter methods when uncertain: create the channel, set frequency, then set duty.
- `Display.init(Display.ST7701, ...)` may occupy backlight/buzzer-related PWM resources. Prefer PWM2 or another verified free PWM channel for servos.
- Avoid software PWM for servos in the frame loop; a 20 ms servo period needs pulse-width precision that normal vision loops cannot provide.
- UART pin names, K230 GPIO pad numbers, and 40Pin physical pin numbers are easy to confuse. Use `hardware-pin-resource-quickref.md` and `scripts/probe_uart2_loopback.py` before claiming a UART wiring is wrong.
- UART0 is usually not the first choice for user peripherals. Prefer UART2 or UART3 unless the board/firmware and wiring are verified.

## Image Processing

- Use ROI, stride, candidate limits, and skip-frame result holding for full-screen `800x480` algorithms.
- `find_rects` and `find_circles` are expensive. Use smaller detection images or strong ROIs unless board testing proves the frame rate is acceptable.
- `merge=True` in blob detection can cost time and can merge nearby targets. Keep it off unless it solves a real fragmentation problem.
- `img.to_lab()` and `img.get_pixel(...)` are not safe cross-firmware assumptions. For offline color calibration, prefer ROI `copy(...)` plus `get_statistics()` when available.
- For black/white targets, Otsu histogram calibration is a useful startup or user-triggered path: sample about 30 frames, discard out-of-range thresholds, average valid thresholds, verify detection for several frames, then fall back to a known-safe default if verification fails. Use `scripts/probe_otsu_threshold.py` as a bounded board-side probe before enabling startup Otsu in a long-running contest template.
- JPEG or image-file save operations are slow. Throttle capture or snapshot saving and keep it out of the per-frame control loop.
- Periodic `print(...)`, complex text drawing, and frequent `gc.collect()` can dominate the frame loop. Throttle them.

## Conservative Syntax And Validation

Use this section before generating a ready-to-copy `main.py` for K230 CanMV.

CanMV MicroPython may accept a smaller or different Python syntax subset than desktop Python. A script can pass desktop `python -m py_compile` and still fail in CanMV IDE K230 with `SyntaxError: invalid syntax`.

For final scripts, prefer plain MicroPython style:

- Avoid f-strings unless the target firmware has already been tested with them.
- Avoid `lambda`, list comprehensions, dict comprehensions, set comprehensions, and generator expressions in final examples.
- Avoid deeply nested inline expressions and complex multi-line function calls for debug printing, logging, or string formatting.
- Prefer simple loops, temporary variables, one statement per line, and `%` formatting or simple string concatenation.
- Keep `try`/`except` blocks simple and use `print("error:", e)` instead of `sys.print_exception(e)` unless the firmware confirms support.

Desktop syntax checks are useful but not sufficient. When hardware is available, also run the script through CanMV IDE or `scripts/run_canmv_raw_repl.py`. When generating or editing `assets/contest-template/` files, keep this conservative style even if desktop Python accepts newer or denser syntax.

## Code Generation Checklist

Before writing final K230 CanMV code:

1. Choose the exact display path: LCD, IDE virtual display, HDMI, or no display.
2. Choose the exact camera path: default `Sensor(id=2)` or a probed alternative.
3. Confirm whether the algorithm needs full-screen capture or lower-resolution detection.
4. Confirm UART pins, baud rate, packet format, and common ground if an external MCU is involved.
5. Put thresholds, pins, frame sizes, UART format, and fallback limits at the top.
6. Apply the conservative syntax rules above before handing over final code.
7. Add visible LCD status for calibration, target found/lost, FPS, and faults.
8. Add cleanup and safe-output behavior before enabling actuators.

## Source Notes

External reference reviewed:

https://github.com/2262727886-stack/mspm0g-contest-skill

The reviewed repository did not include a `LICENSE` file in the cloned root even though its README displayed an MIT badge, so this skill paraphrases and rewrites useful patterns instead of copying the 49 KB `k230.md` table or source scripts verbatim.
