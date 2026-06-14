# API Manual Routing

Official API index: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/

Use this file to choose the exact official API page before relying on memory for unfamiliar K230 CanMV APIs. The official API chapter notes that content is transferred from Canaan API docs; when precision matters, compare with the current online page and the user's firmware.

## Core MicroPython APIs

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

## Standard and MicroPython Library APIs

- `utime`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/utime.html
- `gc`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/gc.html
- `os/uos`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/uos.html
- `hashlib`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/hashlib.html
- `ucryptolib`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/standard/ucryptolib.html
- `uctypes`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/uctypes.html
- `network`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/network.html
- `socket`: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/socket.html

## Image and Multimedia APIs

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

## AI and nncase APIs

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
- For final `main.py` syntax style, use `canmv-micropython-compatibility.md`; `python -m py_compile` is not a CanMV parser test.
