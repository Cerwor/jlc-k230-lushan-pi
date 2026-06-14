# Official Links

Use these links as the source index for LCKFB/JLC Lushan Pi K230 work.

If a link moves or an API page changes meaningfully, update the relevant reference file and record the change in `maintenance.md#revision-log`.

## Board and Setup

- Main wiki: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/
- Quick start: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/quick-start.html
- Downloads: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/download.html
- CanMV firmware: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/canmv-firmware.html
- CanMV IDE K230: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/canmv-ide-k230.html
- Offline run: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/ide-usage/offline-run.html
- FAQ: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/faq.html

Quick-start caution: the K230 and Lite-K230D boards use different firmware images. Tell the user to select the firmware matching the exact board before writing the TF card.

## Hardware

- Lushan Pi K230 main board overview: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/lushan-pi-k230.html
- Schematic: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/schematic.html
- Schematic diagrams and hardware blocks: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/diagram.html
- 3.1-inch MIPI screen expansion board: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/lckfb-mipi-3.1inch-screen.html
- HDMI expansion board: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/hdmi.html

3.1-inch screen notes:

- It connects to Lushan Pi through the 31P MIPI cable and 6P touch cable.
- The expansion board has a 3.1-inch screen, onboard backlight driver, microphone/speaker pogo pin related circuits, and touch interface.
- Its backlight circuit uses an I2C-to-PWM chip to drive the expansion board backlight driver. If I2C brightness control is not configured, the backlight is pulled up and normally turns on at power-up.

## Base Examples

- MicroPython basics: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/micropython-basic.html
- GPIO and FPIOA: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/gpio-fpioa.html
- PWM: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/pwm.html
- UART: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/uart.html
- ADC: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/adc.html
- TIMER: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/timer.html
- WDT: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/basic/wdt.html

The wiki currently marks the basic I2C tutorial as waiting for update. For I2C work, use the API manual and verify with the user's firmware.

## Camera, Display, and Image Recognition

- Use camera: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/use-sensor.html
- Display image: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/display.html
- Image drawing: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-draw.html
- Image processing: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-processing.html
- Feature detection: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/img-feature-detect.html
- Color recognition: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/color_detection.html
- Code recognition: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/image-recog/code-classif.html

## API Manuals

- API index: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/
- API routing: see `api-manual-routing.md`
- FPIOA API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/fpioa.html
- Pin API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/pin.html
- PWM API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/pwm.html
- UART API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/uart.html
- I2C API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/i2c.html
- SPI API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/micropython/spi.html
- Sensor API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/sensor.html
- Display API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/display.html
- Image API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/multimedia/image.html
- nncase runtime API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/nncase/nncase_runtime.html
- PipeLine API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/pipeline_module_api.html
- Ai2d API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/ai2d_module_api.html
- AIBase API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/aibase_module_api.html
- YOLO API: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/yolo_module_api.html
