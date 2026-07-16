# Sources and Boundaries

Use this file to verify applicability, official source links, and exact API pages before relying on uncertain K230 CanMV facts.

This file intentionally combines the previous source index, API routing table, and usage boundaries because these are normally needed together when a task depends on firmware version, board wiring, API signatures, or official documentation.

## Scope

Use this reference for scope limits, official source links, API manual routing, and claims that need board or documentation verification.

## Contents

- Applicability Boundaries
- Official Source Index
- API Manual Routing
- Routing Rules

## Applicability Boundaries

### Good Fit

Use this skill directly for:

- LCKFB/JLC Lushan Pi K230-CanMV board work.
- CanMV MicroPython examples and contest projects.
- 3.1-inch MIPI LCD workflows using `Display.ST7701`.
- Camera preview, LCD display, image processing, color/feature/code recognition.
- GPIO/FPIOA, PWM, UART, I2C, SPI bring-up with official pin verification.
- YOLOv5, YOLOv8, YOLO11, KModel, PipeLine, Ai2d, and AIBase workflows on CanMV.
- Offline deployment using `main.py`, optional `boot.py`, and TF-card storage.
- Contest project scaffolding from `assets/contest-template/`.

### Ask Before Proceeding

Ask for details or inspect local files before:

- Using a specific CanMV IDE path.
- Using a specific K230 SDK/toolchain path.
- Using a user-provided schematic, custom carrier board, expansion board, or cable wiring.
- Assuming a `.kmodel` path, labels order, model input size, or task type.
- Choosing exact UART/I2C/SPI pins for external modules.
- Driving motors, servos, relays, high-current loads, or any actuator that can damage hardware.
- Editing the user's prior code if file encoding appears non-UTF-8 or comments show mojibake.
- Saving code to the board, modifying TF-card contents, or using IDE offline-save actions. Default to providing files only.

### Do Not Assume

Do not assume:

- The user's machine has the same drive letters or paths as the original development machine.
- Firmware APIs are identical across CanMV versions.
- Desktop Python syntax compatibility proves CanMV MicroPython compatibility.
- Lushan Pi K230 and Lite-K230D firmware/images are interchangeable.
- `UART0` is available for user peripherals.
- ADC accepts 3.3 V. K230 ADC max is 1.8 V.
- GPIO can tolerate signals above 3.3 V.
- A physical pin mapping is correct without official pin tables, `fpioa.help(...)`, schematic evidence, or a known working user example.

### Out of Scope or Needs Extra Sources

Use other sources or ask for artifacts for:

- Full nncase model conversion from training framework to `.kmodel` when export scripts, model files, or conversion logs are missing.
- K230 SDK kernel/RT-Smart internals beyond the official wiki/API pages and user-provided source.
- Non-LCKFB K230 boards with different pinout, power, display, or camera routing.
- Electrical design review for high-power systems; provide checklists, not safety guarantees.
- Guaranteed contest compliance; verify against the current competition rules and hardware constraints.

### Response Boundary

When uncertainty matters, state the uncertainty and give a verification step:

- For pins: verify with `fpioa.help(...)` or the schematic before wiring.
- For firmware: confirm the board firmware string and compare API behavior.
- For final scripts: desktop `py_compile` is not enough; test in CanMV IDE or raw REPL when hardware is available.
- For deployment: test after a full power cycle, not only IDE green-run.
- For offline delivery: provide `main.py`; the user copies it to SD card unless they explicitly ask Codex to save it.
- For actuators: test with outputs disabled or clamped first.

## Official Source Index

Use these links as the source index for LCKFB/JLC Lushan Pi K230 work. If a link moves or an API page changes meaningfully, update the relevant reference file and record the change in `maintenance.md#tested-baseline`; put long chronological test history in repository-level `docs/BOARD_TEST_LOG.md` when available.

### Board and Setup

- Main wiki: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/
- Quick start: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html
- Downloads: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/download.html
- CanMV firmware: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/canmv-firmware.html
- CanMV IDE K230: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/canmv-ide-k230.html
- Offline run: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/ide-usage/offline-run.html
- FAQ: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/faq.html

Quick-start caution: the K230 and Lite-K230D boards use different firmware images. Tell the user to select the firmware matching the exact board before writing the TF card.

### Hardware

- Lushan Pi K230 main board overview: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/lushan-pi-k230.html
- Schematic: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/schematic.html
- Schematic diagrams and hardware blocks: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/diagram.html
- 3.1-inch MIPI screen expansion board: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/lckfb-mipi-3.1inch-screen.html
- HDMI expansion board: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/hdmi.html

3.1-inch screen notes:

- It connects to Lushan Pi through the 31P MIPI cable and 6P touch cable.
- The expansion board has a 3.1-inch screen, onboard backlight driver, microphone/speaker pogo pin related circuits, and touch interface.
- Its backlight circuit uses an I2C-to-PWM chip to drive the expansion board backlight driver. If I2C brightness control is not configured, the backlight is pulled up and normally turns on at power-up.

### Base Examples

- MicroPython basics: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/micropython-basic.html
- GPIO and FPIOA: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/gpio-fpioa.html
- PWM: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/pwm.html
- UART: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/uart.html
- ADC: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/adc.html
- TIMER: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/timer.html
- WDT: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/wdt.html

The wiki currently marks the basic I2C tutorial as waiting for update. For I2C work, use the API manual and verify with the user's firmware.

### Camera, Display, and Image Recognition

- Use camera: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/use-sensor.html
- Display image: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/display.html
- Image drawing: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-draw.html
- Image processing: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-processing.html
- Feature detection: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-feature-detect.html
- Color recognition: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/color_detection.html
- Code recognition: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/code-classif.html

### AI Demo and Model Deployment

- AI demo framework: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/ai-demo/profile.html
- CanMV K230 AI development and model conversion: https://www.kendryte.com/k230_canmv/en/main/ai_dev_doc.html
- nncase model compilation API: https://www.kendryte.com/k230_rtos/en/main/api_reference/nncase/nncase_compile.html
- nncase simulator API: https://www.kendryte.com/k230_rtos/en/main/api_reference/nncase/nncase_simulator.html
- nncase runtime/version compatibility guide: https://www.kendryte.com/k230/en/main/03_other/K230_SDK_Updating_nncase_Runtime_Library_Guide.html

Use the AI demo framework page for overall PipeLine/runtime structure. For exact YOLO and nncase APIs, use the API routing section below. Treat model conversion tools and nncase versions as toolchain-sensitive; verify against the user's conversion script, firmware, and conversion logs.

## API Manual Routing

Official API index: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/

Use this section to choose the exact official API page before relying on memory for unfamiliar K230 CanMV APIs. The official API chapter notes that content is transferred from Canaan API docs; when precision matters, compare with the current online page and the user's firmware.

### Core MicroPython APIs

- `Pin`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/pin.html
- `FPIOA`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/fpioa.html
- `PWM`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/pwm.html
- `UART`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/uart.html
- `I2C`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/i2c.html
- `SPI`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/spi.html
- `ADC`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/adc.html
- `Timer`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/timer.html
- `WDT`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/wdt.html
- `RTC`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/rtc.html
- `machine`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/machine.html
- `TOUCH`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/touch.html
- `LED`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/led.html
- `SPI_LCD`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/spi_lcd.html

### Standard and MicroPython Library APIs

- `utime`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/utime.html
- `gc`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/gc.html
- `os/uos`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/uos.html
- `hashlib`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/hashlib.html
- `ucryptolib`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/ucryptolib.html
- `uctypes`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/uctypes.html
- `network`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/network.html
- `socket`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/socket.html

### Image and Multimedia APIs

- `Sensor`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/sensor.html
- `Display`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/display.html
- `Media`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/media.html
- `Image`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/image.html
- `Audio`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/audio.html
- `VDEC`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/vdec.html
- `VENC`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/venc.html
- `MP4`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/mp4.html
- Player: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/player.html
- `RTSP`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/rtsp.html
- `PM`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/pm.html
- `lvgl`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/lvgl.html

### AI and nncase APIs

- `nncase_runtime`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/nncase/nncase_runtime.html
- `PipeLine`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/pipeline_module_api.html
- `Ai2d`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/ai2d_module_api.html
- `AIBase`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/aibase_module_api.html
- `YOLO`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/yolo_module_api.html

## Routing Rules

- For any API that has already failed on-board, trust the board error and current firmware over memory; then check the matching API page.
- For `sys.print_exception`, use the local firmware finding in `troubleshooting.md`: it may be absent, so templates prefer `print("error:", e)`.
- For image operations such as `find_rects`, `find_blobs`, drawing functions, ROI, thresholding, and image format limits, read the `Image` API page and compare with `official-basic-image-patterns.md`.
- For display or panel errors, read the `Display` API page and `troubleshooting.md#lcd-or-display-problems`.
- For AI demo code, read both the specific module API and the board's `/sdcard/examples/...` script if available.
- For final `main.py` syntax style, use `canmv-api-known-issues.md#conservative-syntax-and-validation`; `python -m py_compile` is not a CanMV parser test.
