# Usage Boundaries

Use this file to decide when the skill is directly applicable, when to ask for more data, and when to avoid confident claims.

## Good Fit

Use this skill directly for:

- LCKFB/JLC Lushan Pi K230-CanMV board work.
- CanMV MicroPython examples and contest projects.
- 3.1-inch MIPI LCD workflows using `Display.ST7701`.
- Camera preview, LCD display, image processing, color/feature/code recognition.
- GPIO/FPIOA, PWM, UART, I2C, SPI bring-up with official pin verification.
- YOLOv5, YOLOv8, YOLO11, KModel, PipeLine, Ai2d, and AIBase workflows on CanMV.
- Offline deployment using `main.py`, optional `boot.py`, and TF-card storage.
- Contest project scaffolding from `assets/contest-template/`.

## Ask Before Proceeding

Ask for details or inspect local files before:

- Using a specific CanMV IDE path.
- Using a specific K230 SDK/toolchain path.
- Using a user-provided schematic, custom carrier board, expansion board, or cable wiring.
- Assuming a `.kmodel` path, labels order, model input size, or task type.
- Choosing exact UART/I2C/SPI pins for external modules.
- Driving motors, servos, relays, high-current loads, or any actuator that can damage hardware.
- Editing the user's prior code if file encoding appears non-UTF-8 or comments show mojibake.
- Saving code to the board, modifying TF-card contents, or using IDE offline-save actions. Default to providing files only.

## Do Not Assume

Do not assume:

- The user's machine has the same drive letters or paths as the original development machine.
- Firmware APIs are identical across CanMV versions.
- Desktop Python syntax compatibility proves CanMV MicroPython compatibility.
- Lushan Pi K230 and Lite-K230D firmware/images are interchangeable.
- `UART0` is available for user peripherals.
- ADC accepts 3.3 V. K230 ADC max is 1.8 V.
- GPIO can tolerate signals above 3.3 V.
- A physical pin mapping is correct without official pin tables, `fpioa.help(...)`, schematic evidence, or a known working user example.

## Out of Scope or Needs Extra Sources

Use other sources or ask for artifacts for:

- Full nncase model conversion from training framework to `.kmodel` when export scripts, model files, or conversion logs are missing.
- K230 SDK kernel/RT-Smart internals beyond the official wiki/API pages and user-provided source.
- Non-LCKFB K230 boards with different pinout, power, display, or camera routing.
- Electrical design review for high-power systems; provide checklists, not safety guarantees.
- Guaranteed contest compliance; verify against the current competition rules and hardware constraints.

## Response Boundary

When uncertainty matters, state the uncertainty and give a verification step:

- For pins: "verify with `fpioa.help(...)` or the schematic before wiring."
- For firmware: "confirm the board firmware string and compare API behavior."
- For final scripts: "desktop `py_compile` is not enough; test in CanMV IDE or raw REPL when hardware is available."
- For deployment: "test after a full power cycle, not only IDE green-run."
- For offline delivery: "provide `main.py`; the user copies it to SD card unless they explicitly ask Codex to save it."
- For actuators: "test with outputs disabled or clamped first."
