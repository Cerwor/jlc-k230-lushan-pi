# Troubleshooting

Use this file as the single debug checklist for Lushan Pi K230 CanMV contest projects. Keep task-specific references focused on normal usage; put failure diagnosis here.

## Scope

Use this reference after probe failures, runtime errors, serial silence, display/camera issues, model-load failures, or actuator bring-up problems.

## Contents

- First Pass
- Probe Result Actions
- Raw REPL or USB Serial Problems
- No Offline Auto-Run
- Camera Problems
- LCD or Display Problems
- GPIO, PWM, UART, I2C, SPI Problems
- CanMV API or Firmware Quirks
- YOLO, KModel, or AI Problems
- Contest Integration Problems

## First Pass

Check in this order:

1. Board model and firmware match: Lushan Pi K230 is not Lite-K230D.
2. Power path is stable: USB, header 5 V, or 8-24 V input.
3. CanMV IDE can connect and run a simple `print(...)` script.
4. The script also runs after reset/power-cycle if it is meant for offline use.
5. The final file is named `main.py` and is in the TF card `sdcard` root.
6. `boot.py` is absent or finishes quickly; it must not block `main.py`.
7. Required files exist on the board at the paths used in code, especially `/data/...` models and labels.
8. On the tested firmware reference, prefer `print("error:", e)` over `sys.print_exception(e)` because `sys.print_exception` may be unavailable.

## Probe Result Actions

Use this table after `scripts/run_board_probe.py` prints `ACCEPT_* status=pass|warn|fail`. Do not enable motors, lasers, or other actuators from a `warn` or `fail` result unless the user deliberately accepts the risk and the next action is bounded.

| Probe | `pass` | `warn` | `fail` |
| --- | --- | --- | --- |
| `ACCEPT_SMOKE` camera/LCD | Continue to the task-specific vision probe. | Re-run once after reset; check camera/LCD cables, display mode, and whether IDE preview or physical LCD is the intended output. | Stop integration; run a minimal print script, then camera-only and display-only checks before any model or actuator code. |
| `ACCEPT_RECT` rectangle target | Enable UART/control only after the displayed `#1` target is the intended rectangle. | Adjust target size/distance/lighting/ROI; remove small competing rectangles; try strict-plus-relaxed `cv_lite`; re-run before motion. | Do not send motion commands; fall back to camera/LCD smoke, then `cv_lite` import probe, then simpler `rectangle_detect.py`. |
| `ACCEPT_CIRCLE` circle target | Use current ROI/radius thresholds for a bounded control test. | Tune ROI, radius window, threshold, and result-hold; circle detection is scene-sensitive, so do a short vision-only confirmation. | Do not integrate control; switch to blob/ring-specific preprocessing or ask for a clearer target design. |
| `ACCEPT_YOLO` runtime/resources | Runtime imports and board resources are available; still validate the user's exact `.kmodel`, labels, input size, and result tuple. | Probe actual model paths and example directories; reduce scan scope if truncated; verify SD-card mount and model package. | Split the issue: imports missing means firmware/library mismatch; model paths missing means board-file/package problem; `.kmodel` load failure means conversion/runtime mismatch and needs user artifacts/logs. |
| `ACCEPT_UART` loopback/TX sweep | Use the passing pin pair and baud rate in final code. | Recheck TX/RX short or external MCU wiring; try `PIN5/PIN6`, `PIN11/PIN12`, and `PIN44/PIN45`; keep common ground. | Do not blame the peripheral first; verify FPIOA mapping, port ownership, baud, and whether another script is using UART. |
| `ACCEPT_RESOURCES` board resources | Use the reported paths rather than hard-coded `/data/...` assumptions. | Treat missing or truncated directories as an SD-card/resource issue; reset and re-run with narrower scan. | Check SD-card insertion, firmware image resources, and whether `/sdcard/main.py` is blocking access. |
| `ACCEPT_LIFECYCLE` camera/display cleanup | Repeated initialization and cleanup completed; continue to bounded recovery testing if the application needs it. | Reset once and repeat; inspect heap drift and cleanup warnings, but do not treat Python heap alone as proof about native media pools. | Stop recovery-loop integration; inspect the first failed cycle and verify `Sensor.stop()`, `Display.deinit()`, then `MediaManager.deinit()` ordering. |
| `ACCEPT_OTSU` threshold | Use the calibrated threshold as a startup or user-triggered value. | Keep the fallback threshold visible on LCD; ask the user to fill the ROI with target/background and re-run. | Do not auto-calibrate in final code; use a manual threshold or a different feature detector. |

## Raw REPL or USB Serial Problems

- On Windows, the board may enumerate as a USB composite device with both `USB Serial Device (COMx)` and `WPD CanMV`; WPD presence does not mean a normal drive letter is available.
- If `scripts/run_canmv_raw_repl.py` fails, close CanMV IDE and any serial terminals, then retry with an explicit port such as `--port COM14`.
- If raw REPL remains unavailable, use `run_board_probe.py --vision <single-mode> --export-main .\probe-export\main.py`. This creates only a local file; run it manually in CanMV IDE or copy it to the SD card only after the normal board-write gate and backup steps.
- If the CanMV USB serial port disappears after removing the SD card, reinsert the SD card and retry; the tested Lushan Pi K230 setup may depend on SD-card CanMV system/resources to bring up the USB serial service.
- If the USB serial port exists but REPL has no echo, check whether `/sdcard/main.py` or `/sdcard/boot.py` is auto-running and blocking REPL. Rename them to `main_disabled.py` or `boot_disabled.py`, reboot, then retry raw REPL.
- If the helper reports that no serial bytes were received, reset or replug the board before retrying; a previous interrupted upload can leave the port openable but silent.
- If the port opens but there is no prompt, send `Ctrl-C`, wait for `MPY: soft reboot` and the ordinary `>>>` prompt, then send `Ctrl-A` to enter raw REPL. The helper script now retries this sequence and prints a handshake log on failure.
- Use `scripts/run_canmv_raw_repl.py --list-ports` to inspect available serial ports. Treat `VID:PID 1209:ABD1` as a tested CanMV hint, not a fixed K230 identity; pass `--port COMx` when the board appears under another VID/PID.
- Use `scripts/mpremote_deploy.py --list-ports` when debugging the `mpremote` deployment path; it uses the same CanMV/K230 port heuristics but its deploy mode writes files to `/sdcard`.
- If the helper reports `Board script raised an exception`, inspect the printed traceback first; the serial connection worked and the uploaded MicroPython code failed on the board.
- If the helper reports `Timed out before raw REPL completion marker`, the uploaded script did not return to raw REPL cleanly. Increase `--timeout` for slow probes, or reset the board before running another script.
- When `--baud` is omitted, `scripts/run_canmv_raw_repl.py` tries `2000000` and then `115200`. During board testing, the same COM14 device sometimes had no bytes at one baud but worked at the other, so prefer omitting `--baud` unless a fixed baud is being diagnosed.
- Use `scripts/run_board_probe.py --vision smoke` as the first hardware test when raw REPL works but camera/LCD behavior is uncertain.
- If `mpremote` hangs while a complex `/sdcard/main.py` is auto-running, send a raw Ctrl-C burst first or use `scripts/mpremote_deploy.py`, which does this before `mpremote ... resume fs cp`.

## No Offline Auto-Run

- Confirm green-run from IDE is not being mistaken for offline deployment.
- Save with `Tools -> save open script to CanMV board (as main.py)` or manually copy `main.py` to the TF card root.
- Add early `print("boot main start")` and LCD status text.
- Temporarily remove or simplify `boot.py`.
- Verify the program has a persistent loop and does not exit immediately.
- Re-run the same file from IDE to catch syntax/runtime errors.

## Camera Problems

- Default board camera is usually `CSI2`; `Sensor()` is equivalent to `Sensor(id=2)` in official notes.
- If a new camera/firmware rejects the normal constructor, run `scripts/run_board_probe.py --vision sensor`. Use the first snapshot-capable mode only as a local workaround until it is board-tested.
- Check FPC orientation, seating, and whether the selected connector matches the code.
- Start with a raw camera/LCD preview before adding AI.
- Reduce resolution if memory pressure or frame drops appear.
- Ensure cleanup order from the template is preserved after exceptions.

## LCD or Display Problems

- For the 3.1-inch MIPI screen, start with `Display.ST7701`, `width=800`, `height=480`.
- Check the 31P MIPI cable and 6P touch cable.
- Use `to_ide=True` while debugging if memory permits.
- Try `Display.VIRT` to separate camera/algorithm issues from physical LCD issues.
- Verify backlight enable/PWM if the image exists in IDE but the physical LCD is dark.

## GPIO, PWM, UART, I2C, SPI Problems

- Confirm all external signals are 3.3 V compatible; ADC max is 1.8 V.
- Map every pad with `FPIOA` before peripheral construction.
- Use `fpioa.help(pin)` or `fpioa.help(func, func=True)` to inspect possible mappings.
- Avoid UART0 for user peripherals; prefer UART2 or UART3.
- For UART, cross TX/RX, share GND, and match baud/data/parity/stop settings.
- If a UART2 loopback test reports transmit success but `rx=0`, do not assume the UART peripheral failed. First run `scripts/run_board_probe.py --vision uart-loopback` to verify whether the physical short is on `PIN5/PIN6`, `PIN11/PIN12`, or `PIN44/PIN45`; tested wiring on `PIN5/PIN6` worked after changing the FPIOA mapping.
- If an external MCU receives nothing, use the all-UART TX sweep selected by `scripts/run_board_probe.py --vision uart-loopback`. Each candidate sends a different Wheeltec-style frame at 9600 baud, so the MCU-side raw-byte/OLED view can identify the actual K230 TX pad.
- For PWM, use one duty representation at a time: `duty`, `duty_u16`, or `duty_ns`.
- For motors/servos, clamp outputs and provide a neutral/stop path in exceptions.

## CanMV API or Firmware Quirks

- Read `references/platform/canmv-api-known-issues.md` before changing working templates because of a single API failure.
- If `img.to_lab()` or `img.get_pixel(...)` is missing, prefer ROI `copy(...)` plus `get_statistics()` instead of per-pixel sampling.
- If dual-channel capture fails on a different firmware, fall back to single-channel full-screen capture with ROI/stride/skip-frame processing; do not discard the dual-channel templates that were board-tested on the user's firmware.
- If `Display.bind_layer(...)` fails, return to the simpler `snapshot -> draw -> Display.show_image(img)` path before debugging OSD/video layers.
- If thresholding is unstable after moving to contest lighting, use a calibration path such as the optional Otsu startup calibration in `offline_threshold_tuner.py`, then keep a visible fallback threshold on LCD.

## YOLO, KModel, or AI Problems

- Validate the `.kmodel` with still-image inference before camera video mode.
- Confirm model family, task type, labels order, `model_input_size`, and input color/layout.
- Confirm the model path exists on board. Do not assume `/data/...`; tested LCKFB SD-card images may place examples and models under `/sdcard/examples/`.
- If `OSError: Kmodel file not exist.` appears, run `scripts/run_board_probe.py --vision resources` or a small `os.listdir(...)` script on the board to find actual `.kmodel` paths.
- If an official YOLO example fails with `RuntimeError: init panel failed`, check display mode. Official examples may default to HDMI; for the 3.1-inch LCD, force `display_mode="lcd"` or use the launcher in `references/vision/yolo-module-patterns.md#board-proven-yolov8-lcd-launcher`.
- For video mode, start with `PipeLine` display only, then add `yolo.run`, then add control logic.
- Lower `rgb888p_size` or skip frames if inference is too slow.
- Call `gc.collect()` periodically and release `yolo.deinit()`/`pl.destroy()` in `finally`.

## Contest Integration Problems

- Disable actuators until perception is stable.
- Add on-screen and serial telemetry for state, FPS, target center, confidence, and output command.
- Add fallback states for no target, low confidence, UART timeout, model load failure, and camera failure.
- Test each module in `examples/` before running integrated `main.py`.
- Keep one known-good backup of the final contest `main.py`.
