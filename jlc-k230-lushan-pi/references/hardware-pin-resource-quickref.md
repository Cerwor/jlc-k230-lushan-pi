# Hardware Pin and Resource Quick Reference

This file distills the official LCKFB/JLC Lushan Pi K230 schematic diagram page into practical hardware notes for coding, wiring, and contest bring-up.

Official source: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/diagram.html

For wiring, voltage, and peripheral failures, use `troubleshooting.md#gpio-pwm-uart-i2c-spi-problems`. For scope boundaries and safety assumptions, use `sources-and-boundaries.md#applicability-boundaries`.

## Scope

Use this reference for Lushan Pi K230 pin, connector, power, UART/FPIOA, camera, display, and board-resource checks.

## Contents

- Safety Rules
- Power Inputs and Outputs
- Boot and Storage
- USB Resources
- GPIO and Header Resources
- Common Pin and Connector Quick Table
- UART and I2C Physical Connectors
- Camera Interfaces
- DSI Display and Touch
- Wi-Fi
- Buttons, LEDs, Audio, and Buzzer
- Mechanical and Test Pads
- Practical Contest Checklist

## Safety Rules

- Standard GPIO and header IO high level is 3.3 V. Do not connect signals above 3.3 V to GPIO.
- K230 ADC inputs support only up to 1.8 V. ADC is not directly exposed on the standard 40-pin header; it is routed to an FPC connector to reduce wrong-wiring risk.
- The board provides 4 ADC inputs through the ADC FPC area, suitable for two potentiometer joysticks.
- Use the original schematic/PDF or `FPIOA.help(...)` for exact pad/function confirmation before final wiring.
- For high-current or battery-powered contest projects, verify power path and current limits before connecting motors, servos, or extra modules.

## Power Inputs and Outputs

The board is designed around several power entry paths:

- USB Type-C power/data.
- 40-pin header 5 V, which can act as 5 V input or external 5 V output depending on power state.
- 8-24 V input through a GH1.25-2P locking connector, stepped down to 5 V.
- Large 2.54 mm pads are also available for higher-current wiring on the 8-24 V path.

Important limits and protections:

- USB Type-C connects to K230 `USB0` as a device port for CanMV host interaction.
- USB input and header 5 V input use overcurrent/ESD/protection circuitry.
- Header 5 V output is limited to about 1 A in the schematic notes.
- USB/pin input-side current limiting is described around 2 A.
- The 8-24 V input uses DCDC buck conversion and includes overvoltage, overcurrent, and reverse-connection protection.
- The DCDC chip supports higher voltage, but the board documentation recommends not exceeding 24 V.
- USB Type-A host output current limiting is about 600 mA.

## Boot and Storage

Boot mode resistors select K230 boot source:

- `BOOT0 = 0`, `BOOT1 = 0`: SPI NOR Flash
- `BOOT0 = 0`, `BOOT1 = 1`: eMMC
- `BOOT0 = 1`, `BOOT1 = 0`: SPI NAND
- `BOOT0 = 1`, `BOOT1 = 1`: SD card

The Lushan Pi K230 currently supports SD-card boot; `BOOT0` and `BOOT1` are pulled high by default.

Storage options:

- Default: self-locking TF card socket for firmware/storage.
- Optional footprint: SD NAND / NAND Flash under the TF-card socket area.
- TF card and SD NAND share the same SDIO signal path and must not be used simultaneously.
- SD NAND is intended for higher mechanical reliability in vibration-heavy projects such as small cars or drones.

## USB Resources

- K230 has two USB ports.
- On this board, `USB0` is used as a `DEVICE` interface for CanMV host/PC interaction through Type-C.
- `USB1` is used as `HOST` for future/optional peripherals such as Ethernet adapters or USB storage.
- The Type-A host interface includes ESD protection and current limiting.

## GPIO and Header Resources

Hardware-level notes:

- `VDDIO_BANK` controls IO high level for each bank; exposed GPIO IO levels are 3.3 V.
- The standard 40-pin header follows Raspberry Pi-style pin layout with 5 V, 3.3 V, GND, and interfaces such as I2C/SPI/UART.
- The board is designed for compatibility with many Raspberry Pi-style expansion modules, but software/pin multiplexing still needs verification.
- The schematic page notes CSI camera connectors also follow Raspberry Pi 5 / Raspberry Pi Zero style mechanical definitions.

Use `official-basic-image-patterns.md` for common GPIO/FPIOA, I2C, PWM, and UART mappings extracted from the official examples.

## Common Pin and Connector Quick Table

Use this as a first-pass wiring map, not as the final authority. It is condensed from the official GPIO/FPIOA 40Pin image and schematic notes. Verify the exact board silkscreen, connector, and active FPIOA mapping before connecting external hardware.

40Pin header notes:

- Physical pin numbers are the Raspberry Pi-style 40Pin header positions.
- `GPIOxx` is the pad label shown by the official 40Pin image. In code, the first argument to `fpioa.set_function(...)` is the pad number; the selected function may be `FPIOA.GPIOxx` or a peripheral constant and is not always numerically identical on every board resource.
- One physical pad can expose many possible functions, but only one function can be active at a time.
- All normal 40Pin GPIO signals are 3.3 V logic. The 40Pin header does not expose ADC.

| Physical pin | CanMV/FPIOA pad | Common functions shown by official 40Pin image | Notes |
| --- | --- | --- | --- |
| 1 | 3V3 | Power | 3.3 V output |
| 2 | 5V | Power | 5 V rail |
| 3 | GPIO49 | I2C0_SDA, UART4_RXD | I2C0 also used around camera resources; verify external pull-ups |
| 4 | 5V | Power | 5 V rail |
| 5 | GPIO48 | I2C0_SCL, UART4_TXD | I2C0 SCL |
| 6 | GND | Ground | Common ground |
| 7 | GPIO2 | GPIO2, JTAG_TCK | Avoid JTAG use unless needed |
| 8 | GPIO3 | UART1_TXD, JTAG_TDI | UART1 possible, not the usual contest UART |
| 9 | GND | Ground | Common ground |
| 10 | GPIO4 | UART1_RXD, JTAG_TDO | UART1 possible, not the usual contest UART |
| 11 | GPIO5 | UART2_TXD, JTAG_TMS | Board-tested UART2 alternate TX pad |
| 12 | GPIO47 | PWM3, I2C4_SDA, UART2_CTS | PWM-capable header pin |
| 13 | GPIO6 | UART2_RXD, JTAG_RST | Board-tested UART2 alternate RX pad |
| 14 | GND | Ground | Common ground |
| 15 | GPIO26 | PDM_CLK | Audio/PDM-related pad |
| 16 | GPIO18 | QSPI0_D2, QSPI1_CS2 | Avoid QSPI functions unless deliberate |
| 17 | 3V3 | Power | 3.3 V output |
| 18 | GPIO19 | QSPI0_D3, QSPI1_CS1 | Avoid QSPI functions unless deliberate |
| 19 | GPIO16 | QSPI0_D0, QSPI1_CS4 | SPI/QSPI-style function |
| 20 | GND | Ground | Common ground |
| 21 | GPIO17 | QSPI0_D1, QSPI1_CS3 | SPI/QSPI-style function |
| 22 | GPIO27 | PDM_IN0 | General input possible after FPIOA mapping |
| 23 | GPIO15 | QSPI0_CLK | SPI/QSPI-style clock |
| 24 | GPIO14 | QSPI0_CS0 | SPI/QSPI-style chip select |
| 25 | GND | Ground | Common ground |
| 26 | GPIO61 | PWM1, I2C0_SDA, QSPI0_CS1 | PWM-capable header pin |
| 27 | GPIO41 | I2C1_SDA, UART1_RXD | I2C1 SDA |
| 28 | GPIO40 | I2C1_SCL, UART1_TXD | I2C1 SCL |
| 29 | GPIO36 | I2C3_SCL, UART4_TXD, PDM_IN2, IIS_D_IN1 | Multi-function pad |
| 30 | GND | Ground | Common ground |
| 31 | GPIO37 | I2C3_SDA, UART4_RXD, PDM_IN0, IIS_D_OUT1 | Multi-function pad |
| 32 | GPIO46 | PWM2, I2C4_SCL, UART2_RTS | PWM-capable header pin |
| 33 | GPIO52 | PWM4, UART3_RTS | Board-tested USR key uses pad 52 as `FPIOA.GPIO53`, so do not reuse blindly |
| 34 | GND | Ground | Common ground |
| 35 | GPIO42 | PWM0, UART1_RTS, QSPI1_D2 | Common PWM0 example pad |
| 36 | GPIO35 | I2C1_SDA, UART3_CTS, IIS_D_OUT0, PDM_IN1 | Multi-function pad |
| 37 | GPIO32 | UART3_TXD, I2C0_SCL, IIS_CLK | UART3 TX alternate on header |
| 38 | GPIO34 | I2C1_SCL, UART3_RTS, IIS_D_IN0, PDM_IN3 | Multi-function pad |
| 39 | GND | Ground | Common ground |
| 40 | GPIO33 | UART3_RXD, I2C0_SDA, IIS_WS | UART3 RX alternate on header |

Common non-40Pin connectors and pads:

| Resource | Known signal/pad | Use |
| --- | --- | --- |
| GH1.25 UART2/IIC2 | UART2_TXD `GPIO11`, UART2_RXD `GPIO12`; also IIC2_SCL/SDA on the same pair | Preferred locking connector for an external MCU when the connector is used |
| UART2 alternate pads | `PIN5/PIN6`, `PIN11/PIN12`, `PIN44/PIN45` on tested firmware | Use `scripts/probe_uart2_loopback.py` when the physical short/wiring is uncertain |
| UART TX sweep candidates | UART1 `GPIO3`, UART2 `GPIO5/GPIO11/GPIO44`, UART3 `GPIO32/GPIO50`, UART4 `GPIO36/GPIO48` | Same probe sends distinctive test frames on each candidate so an external MCU can identify the real TX pad |
| GH1.25 UART3 | UART3_TXD `GPIO50`, UART3_RXD `GPIO51` | User-available serial on newer CanMV firmware; verify occupation on old Linux+RT-Smart firmware |
| USR button | Physical USR tested as `BUTTON_PAD=52`, `FPIOA.GPIO53`, `Pin(53, Pin.PULL_DOWN)` | Idle `0`, pressed `1`; do not use `RST` or `BOOT` as normal user input |
| Buzzer | `GPIO43 -> FPIOA.PWM1` in official examples | Passive buzzer, nominal loudest frequency around 4000 Hz |
| LCD backlight | `GPIO25 -> FPIOA.PWM5` in board-side examples | Backlight enable/PWM, verify with display hardware |
| ADC FPC | 4 ADC channels, max 1.8 V | Not on 40Pin header; suitable for two joystick potentiometers with level awareness |

## UART and I2C Physical Connectors

The board exposes additional communication through GH1.25-4P locking connectors and large pads.

Key resources:

- One extra GH1.25-4P interface can be configured as `UART2` or `IIC2`.
- The connector is intended for stable physical connection in mobile/contest projects.
- Large 2.54 mm test pads expose power and signals, including `USB5V`, `PIN5V`, `8V-24V`, `UART3`, `UART0`, `UART2/IIC2`, and audio signals.
- On tested firmware, `FPIOA.help(...)` reported UART2 can map to `PIN5/PIN6`, `PIN11/PIN12`, or `PIN44/PIN45`. Use the board silkscreen/schematic to match these K230 pin names to the actual connector or pad being touched.
- The current setup has passed UART2 loopback on `PIN5/PIN6`. Reconfirm a new connector or board with `python .\scripts\run_board_probe.py --vision uart-loopback --port COM14`; exact historical byte counts remain in repository `docs/BOARD_TEST_LOG.md`.

UART occupation notes from the schematic page:

- With `Linux + RT-Smart` firmware, `UART0` is occupied by the Linux side and `UART3` by RT-Smart.
- With newer CanMV firmware after 2024-09-15, the firmware is `RT-Smart only`; the small core does not occupy UART resources, `UART0` is still occupied by RT-Smart, and `UART3` can be called by the user.
- For CanMV examples, prefer user-available UARTs such as `UART2` or `UART3`, and avoid claiming `UART0` is free.

## Camera Interfaces

The board provides three CSI camera connectors:

- `CSI2` is the default camera interface and uses a vertical 0.5 mm pitch FPC connector.
- The other two camera connectors use horizontal 0.5 mm pitch FPC connectors.
- All three camera connectors are designed to be compatible with Raspberry Pi 5 / Raspberry Pi Zero CSI interface definitions.

K230 camera lane combinations:

- Three-camera mode: `2 lane + 2 lane + 2 lane`.
- Two-camera mode: `2 lane + 4 lane`, where the 4-lane camera is a fixed `CSI0 + CSI1` combination.

Hardware note:

- On this board, all three camera connectors are 2-lane connectors.
- `CSI0` and `CSI1` are length-matched in PCB layout so they can be combined through an external expansion board for higher-resolution 4-lane cameras.

Software implication:

- In CanMV camera examples, default to `Sensor()` / `Sensor(id=2)` unless the user explicitly selects another CSI port.

## DSI Display and Touch

Display resources:

- The board has a MIPI-DSI interface.
- The DSI connector layout is compatible with the Taishan Pi style and common MIPI display pinouts.
- The selected 31-pin MIPI interface can theoretically connect to common larger MIPI screens, but software adaptation may be required.
- The 3.1-inch screen expansion board is the default small display target for this skill.

Backlight notes:

- `LCD_EN` can be used as a simple enable level or as a PWM signal.
- As a simple enable signal, it controls backlight on/off.
- As PWM, it can adjust average backlight brightness by duty cycle.
- The board-side backlight driver is configured for higher-current compatibility, while the 3.1-inch screen expansion board has its own small-screen backlight driver.

Touch interface notes:

- Touch connector is compatible with the Taishan Pi touch cable position/pinout.
- Touch I2C has default 4.7 kOhm pull-up resistors on the board, so the screen/expansion board side does not need additional pull-ups.
- Touch signal lines include TVS protection for ESD.

## Wi-Fi

- Board defaults to onboard ceramic antenna.
- IPEX external antenna support is available by moving a 0-ohm resistor from the onboard antenna path to the IPEX path.
- Default Wi-Fi module is RTL8189.
- The design reserves support for AP6212 with additional component population.

## Buttons, LEDs, Audio, and Buzzer

LEDs and buttons:

- Power indicator LED lights when 3.3 V is present.
- Onboard RGB LED is user-controllable through three separate pins.
- The three onboard buttons are reset, BOOT0, and user key.
- BOOT0 can be held before power-on for USB flashing scenarios.
- A live CanMV test mapped the physical `USR` key as `BUTTON_PAD = 52`, `FPIOA.GPIO53`, `Pin(53, Pin.IN, Pin.PULL_DOWN)`: idle is `0`, pressed is `1`. Do not use `RST` or `BOOT` as normal user-input buttons in contest templates.

Audio:

- The board exposes a 3.5 mm headphone interface and onboard microphone.

Buzzer:

- The board has an onboard passive electromagnetic buzzer.
- It is intended to be driven with a square wave/PWM.
- The buzzer's loudest nominal frequency is around 4000 Hz.
- Use PWM for beep tones or simple melodies.
- The buzzer drive circuit includes protection for the MOSFET because the buzzer is an inductive load.

## Mechanical and Test Pads

- Screw holes support M3 bolts; hole inner diameter is 3.2 mm.
- Large 2.54 mm pads can be soldered directly to wires or headers.
- Large pads expose multiple power and signal resources for DIY and contest wiring.

## Practical Contest Checklist

Before wiring or code generation:

- Confirm supply path: USB, header 5 V, or 8-24 V input.
- Confirm module current does not exceed board output limits.
- Confirm all GPIO signal levels are 3.3 V compatible.
- Do not connect 3.3 V directly to ADC; ADC max is 1.8 V.
- Use `UART2` or `UART3` for external controllers, not `UART0`.
- Default camera is `CSI2`.
- Default LCD is MIPI DSI with `Display.ST7701`, 800x480.
- Use FPIOA mapping in code and verify with official pin table or `fpioa.help(...)`.
- For mobile projects, consider TF card vibration risk and keep boot/storage reliable.
