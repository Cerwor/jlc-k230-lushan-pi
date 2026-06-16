# Troubleshooting

Use this file as the single debug checklist for Lushan Pi K230 CanMV contest projects. Keep task-specific references focused on normal usage; put failure diagnosis here.

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

## No Offline Auto-Run

- Confirm green-run from IDE is not being mistaken for offline deployment.
- Save with `Tools -> save open script to CanMV board (as main.py)` or manually copy `main.py` to the TF card root.
- Add early `print("boot main start")` and LCD status text.
- Temporarily remove or simplify `boot.py`.
- Verify the program has a persistent loop and does not exit immediately.
- Re-run the same file from IDE to catch syntax/runtime errors.

## Camera Problems

- Default board camera is usually `CSI2`; `Sensor()` is equivalent to `Sensor(id=2)` in official notes.
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
- For PWM, use one duty representation at a time: `duty`, `duty_u16`, or `duty_ns`.
- For motors/servos, clamp outputs and provide a neutral/stop path in exceptions.

## YOLO, KModel, or AI Problems

- Validate the `.kmodel` with still-image inference before camera video mode.
- Confirm model family, task type, labels order, `model_input_size`, and input color/layout.
- Confirm the model path exists on board. Do not assume `/data/...`; tested LCKFB SD-card images may place examples and models under `/sdcard/examples/`.
- If `OSError: Kmodel file not exist.` appears, run `scripts/probe_board_resources.py` or a small `os.listdir(...)` script on the board to find actual `.kmodel` paths.
- If an official YOLO example fails with `RuntimeError: init panel failed`, check display mode. Official examples may default to HDMI; for the 3.1-inch LCD, force `display_mode="lcd"` or use the launcher in `yolo-module-patterns.md#board-proven-yolov8-lcd-launcher`.
- For video mode, start with `PipeLine` display only, then add `yolo.run`, then add control logic.
- Lower `rgb888p_size` or skip frames if inference is too slow.
- Call `gc.collect()` periodically and release `yolo.deinit()`/`pl.destroy()` in `finally`.

## Contest Integration Problems

- Disable actuators until perception is stable.
- Add on-screen and serial telemetry for state, FPS, target center, confidence, and output command.
- Add fallback states for no target, low confidence, UART timeout, model load failure, and camera failure.
- Test each module in `examples/` before running integrated `main.py`.
- Keep one known-good backup of the final contest `main.py`.
