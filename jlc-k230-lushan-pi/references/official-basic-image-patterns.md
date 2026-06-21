# Official Basic and Image Recognition Patterns

These notes distill the LCKFB/JLC Lushan Pi K230 official wiki pages for GPIO/FPIOA, PWM, UART, and image-recognition examples. Prefer these defaults before inventing new examples.

For failures, route to `troubleshooting.md`: `#gpio-pwm-uart-i2c-spi-problems` for peripherals, `#camera-problems` for sensor issues, `#lcd-or-display-problems` for display issues, and `#yolo-kmodel-or-ai-problems` for model-related issues.

## Contents

- GPIO and FPIOA
- PWM
- UART
- Camera and Display
- Image Drawing
- Image Processing
- Color Recognition
- Feature Detection
- Circle Detection
- Code Recognition

## GPIO and FPIOA

FPIOA is the K230 pin-multiplexing mechanism. Configure the physical GPIO pad function before constructing `Pin`, `UART`, `PWM`, or other peripheral objects.

Core rules:

- One pad can only use one active function at a time.
- 40-pin header GPIO levels are 3.3 V.
- The standard 40-pin header does not expose ADC; K230 ADC is limited to 1.8 V and is routed through FPC instead.
- `I2C0_SCL/SDA` are `GPIO48/GPIO49`; `I2C1_SCL/SDA` are `GPIO40/GPIO41`.
- GH1.25 UART2 is `TX: GPIO11`, `RX: GPIO12`.
- Tested firmware also reports UART2 alternate FPIOA pairs: `TX/RX = PIN5/PIN6`, `PIN11/PIN12`, or `PIN44/PIN45`. Do not confuse K230 `PIN11/PIN12` with a 40-pin header's physical pin numbers.
- GH1.25 UART3 is `TX: GPIO50`, `RX: GPIO51`.
- UART0 is used as an internal RT-Smart console on the board; avoid using it in CanMV examples.
- Current official GPIO notes say CanMV firmware does not support GPIO interrupt mode; use polling, timers, or firmware-specific verification.

Useful introspection:

```python
from machine import FPIOA

fpioa = FPIOA()
fpioa.help()                 # print all pin functions
fpioa.help(38)               # inspect one pin
fpioa.help(FPIOA.UART2_TXD, func=True)  # find pins for a function
```

GPIO output/input skeleton:

```python
from machine import FPIOA, Pin

fpioa = FPIOA()
fpioa.set_function(2, FPIOA.GPIO2)
io = Pin(2, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
io.value(1)
```

For buttons, verify the board wiring and pull direction. Use software debounce for contest projects.

## PWM

Always configure the pad as a PWM function before creating `PWM`.

Official example mappings include:

- `GPIO47 -> FPIOA.PWM3`
- `GPIO61 -> FPIOA.PWM1`
- `GPIO46 -> FPIOA.PWM2`
- `GPIO52 -> FPIOA.PWM4`
- `GPIO42 -> FPIOA.PWM0`
- `GPIO43 -> FPIOA.PWM1` for buzzer drive
- `GPIO25 -> FPIOA.PWM5` for screen backlight drive on board-side examples

The `PWM` constructor is:

```python
pwm = PWM(channel, freq=-1, duty=-1, duty_u16=-1, duty_ns=-1)
```

Use exactly one duty representation at a time: `duty`, `duty_u16`, or `duty_ns`.

Baseline 2 kHz / 50 percent example:

```python
from machine import PWM, FPIOA

fpioa = FPIOA()
fpioa.set_function(42, FPIOA.PWM0)

pwm = PWM(0)
pwm.freq(2000)
pwm.duty_u16(32768)
print(pwm.duty_u16())
```

For contest actuators:

- Use constants for channel, pin, frequency, min/max duty, and neutral duty.
- Clamp duty before writing.
- Call `pwm.deinit()` in cleanup if the script owns the channel.
- For servo-style control, prefer `duty_ns` or a clearly documented conversion rather than magic duty percentages.

## UART

For CanMV examples, prefer UART2 on the first GH1.25 connector unless the user has a reason to use another bus:

```python
from machine import UART, FPIOA

fpioa = FPIOA()
fpioa.set_function(11, FPIOA.UART2_TXD)
fpioa.set_function(12, FPIOA.UART2_RXD)

uart = UART(
    UART.UART2,
    baudrate=115200,
    bits=UART.EIGHTBITS,
    parity=UART.PARITY_NONE,
    stop=UART.STOPBITS_ONE,
)
```

Constructor fields:

- `id`: `UART.UART1`, `UART.UART2`, `UART.UART3`, or `UART.UART4`
- `baudrate`: default 115200
- `bits`: commonly `UART.EIGHTBITS`
- `parity`: commonly `UART.PARITY_NONE`
- `stop`: commonly `UART.STOPBITS_ONE`

Send text:

```python
uart.write("Hello,LuShan-Pi!\n")
```

Send binary:

```python
uart.write(bytes([0x01, 0x02, 0x03, 0x04]))
```

Receive:

```python
data = uart.read()
if data:
    print("Received:", data)
    uart.write("UART2 Received:%s\n" % data)
```

Official notes mark `readline` and `readinto` examples as needing more testing. For robust contest communication, use `uart.read()` plus a small packet parser, timeout handling, and optional checksum.

When loopback wiring is uncertain, run `scripts/probe_uart2_loopback.py`. It scans the common UART2 FPIOA pairs before opening UART2. A live test found a user's wire on `PIN5/PIN6`; the default `PIN11/PIN12` UART2 template therefore transmitted but received `rx=0`.

The same helper also performs a bounded all-UART TX sweep after the loopback test. It sequentially maps common header/connector TX candidates for UART1, UART2, UART3, and UART4, then sends a short Wheeltec-style `FF FE pan tilt 00 00 00 BCC` frame at 9600 baud with a different `pan` byte for each candidate. Use this when an external MCU receives nothing and the physical K230 TX pad is uncertain. Watch the MCU-side raw bytes or OLED debug page to identify which candidate arrives.

Common sweep candidates:

| Label | UART | K230 pad | Typical physical use |
| --- | --- | --- | --- |
| `UART1_P8_GPIO3` | UART1 TXD | GPIO3 | 40Pin physical pin 8 |
| `UART2_P11_GPIO5` | UART2 TXD | GPIO5 | 40Pin physical pin 11 |
| `UART2_GH_GPIO11` | UART2 TXD | GPIO11 | GH1.25 UART2/IIC2 connector |
| `UART2_ALT_GPIO44` | UART2 TXD | GPIO44 | firmware-reported alternate |
| `UART3_P37_GPIO32` | UART3 TXD | GPIO32 | 40Pin physical pin 37 |
| `UART3_GH_GPIO50` | UART3 TXD | GPIO50 | GH1.25 UART3 connector |
| `UART4_P29_GPIO36` | UART4 TXD | GPIO36 | 40Pin physical pin 29 |
| `UART4_P5_GPIO48` | UART4 TXD | GPIO48 | 40Pin physical pin 5 |

Debug checklist:

- Cross TX/RX between devices.
- Share GND.
- Confirm voltage level compatibility.
- Match baud rate, data bits, parity, and stop bits.
- Use hex display in the serial assistant when sending binary packets.
- Call `uart.deinit()` if the script no longer uses the port.

## Camera and Display

Lushan Pi K230 supports three sensor ids. The official Sensor page notes the board default camera interface is CSI2; `Sensor()` is equivalent to `Sensor(id=2)` for the default camera.

Display modes:

- `Display.VIRT`: IDE framebuffer only, useful when no LCD/HDMI is attached.
- `Display.ST7701`: 3.1-inch MIPI LCD, default `800x480@30`.
- `Display.LT9611`: HDMI expansion board, often `1920x1080@30`.

Ordering rules:

- Call `Display.init(...)` before `MediaManager.init()`.
- Call `sensor.stop()` before `Display.deinit()`.
- Call `Display.deinit()` before `MediaManager.deinit()`.

Recommended display selector:

```python
DISPLAY_MODE = "LCD"  # "VIRT", "LCD", or "HDMI"

if DISPLAY_MODE == "VIRT":
    DISPLAY_WIDTH = ALIGN_UP(1920, 16)
    DISPLAY_HEIGHT = 1080
elif DISPLAY_MODE == "LCD":
    DISPLAY_WIDTH = 800
    DISPLAY_HEIGHT = 480
elif DISPLAY_MODE == "HDMI":
    DISPLAY_WIDTH = 1920
    DISPLAY_HEIGHT = 1080
else:
    raise ValueError("unknown DISPLAY_MODE")
```

For LCD:

```python
Display.init(Display.ST7701, width=800, height=480, to_ide=True)
```

Use `to_ide=True` when simultaneous IDE preview is helpful, but remember it costs memory and bandwidth.

## Image Drawing

Use drawing for debugging, data annotation, simple UI, and visualizing algorithm results.

CanMV supports OpenMV-style drawing and adds `draw_string_advanced` for Chinese strings:

```python
img.draw_string_advanced(10, 10, 32, "HELLO", color=(255, 0, 0))
```

For contest overlays, draw:

- FPS
- target center and confidence
- current state
- UART command or PWM output
- ROI rectangle
- thresholds or mode name when tuning

Prefer large, high-contrast text on the 3.1-inch screen.

## Image Processing

Most official image-processing APIs support only `RGB565` or `GRAYSCALE`; avoid compressed/Bayer images unless a specific API allows them.

Use camera input for real-time/dynamic testing and TF-card images for repeatable algorithm tuning. For contest tasks, keep both modes if possible:

- live camera mode for final behavior
- file image mode for repeatable threshold/debug tests

Official examples commonly use:

```python
sensor_id = 2
picture_width = 400
picture_height = 240
DISPLAY_MODE = "LCD"
```

Use lower processing resolutions for classical image processing to improve frame rate.

If the user asks for the 3.1-inch LCD, default to full-screen `800x480` display. When the algorithm uses a lower processing resolution such as `400x240`, be explicit whether the script shows a centered small debug image or uses low-resolution detection with full-screen display and scaled overlays.

## Color Recognition

Official color recognition uses LAB thresholding and blob analysis:

1. Capture image.
2. Convert or interpret color in LAB-friendly threshold space.
3. Match pixels by threshold.
4. Group matching pixels into blobs.
5. Draw and output blob position/size/shape data.

Why LAB:

- L separates brightness from color.
- A represents green-to-red.
- B represents blue-to-yellow.
- LAB is usually more stable for color recognition than raw RGB under changing light.

Contest guidance:

- Define thresholds as constants at the top.
- Add an ROI to avoid false detections.
- Print and overlay blob center, area, and confidence-like size.
- Tune thresholds at the actual contest lighting site.
- For black/white targets, use an Otsu calibration pass when fixed grayscale thresholds are brittle: sample around 30 frames, discard thresholds outside a sane range, average the remaining values, verify several detection frames, then fall back to a known default if verification fails. `scripts/probe_otsu_threshold.py` is the bounded board-side probe; `assets/contest-template/examples/offline_threshold_tuner.py` includes the same idea as an optional startup path through `ENABLE_STARTUP_OTSU`.

## Feature Detection

The official line-segment example uses `find_line_segments`, based on LSD-style line detection:

```python
lines = img.find_line_segments(roi=ROI, merge_distance=0, max_theta_difference=15)
```

Key parameters:

- `roi`: `(x, y, w, h)` region of interest
- `merge_distance`: max pixel distance for merging nearby segments
- `max_theta_difference`: max angle difference for merging segments

This method is accurate but relatively slow. Use ROI and smaller processing images for real-time line tracking.

It does not support compressed or Bayer images.

## Circle Detection

Official circle detection uses `image.find_circles(...)`, a Hough-transform style method. It is useful for circles, rings, round marks, balls, coins, and circular target centers. Keep this section as the official API baseline; for contest strategy, board-tested parameters, LCD scaling, and FPS tradeoffs, route to `circle-detection-patterns.md`.

Core API shape:

```python
circles = img.find_circles(roi=ROI,
                           x_stride=4,
                           y_stride=4,
                           threshold=2500,
                           x_margin=10,
                           y_margin=10,
                           r_margin=10)
```

Performance warning:

- Do not run `find_circles` over full `800x480` by default; it can make FPS too low for live contest control.
- Use `assets/contest-template/examples/circle_detect.py` and `circle-detection-patterns.md` for full-screen LCD display plus low-resolution circle detection.
- ROI coordinates belong to the detection image. Scale circle center/radius back to LCD coordinates before drawing or sending control coordinates.

`find_circles` does not support compressed or Bayer images.

## Code Recognition

For barcode/QR/AprilTag tasks:

- Use an ROI when possible.
- Keep the code in the sharp-focus region.
- Prefer adequate lighting and avoid motion blur.
- For 1D barcodes, a long narrow scan window is often faster.
- The official docs note the small Lushan Pi board QR code is difficult for the supplied fixed-focus camera because the code is small and the lens does not support zoom.
- CanMV IDE can generate AprilTags through Tools -> Machine Vision -> AprilTag generator -> TAG36H11 family.

Barcode/code recognition APIs generally do not support compressed or Bayer images.
