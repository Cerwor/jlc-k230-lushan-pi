# Hardware Pin and Resource Quick Reference

This file distills the official LCKFB/JLC Lushan Pi K230 schematic diagram page into practical hardware notes for coding, wiring, and contest bring-up.

Official source: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/open-source-hardware/diagram.html

For wiring, voltage, and peripheral failures, use `troubleshooting.md#gpio-pwm-uart-i2c-spi-problems`. For scope boundaries and safety assumptions, use `usage-boundaries.md`.

## Contents

- Safety Rules
- Power Inputs and Outputs
- Boot and Storage
- USB Resources
- GPIO and Header Resources
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

## UART and I2C Physical Connectors

The board exposes additional communication through GH1.25-4P locking connectors and large pads.

Key resources:

- One extra GH1.25-4P interface can be configured as `UART2` or `IIC2`.
- The connector is intended for stable physical connection in mobile/contest projects.
- Large 2.54 mm test pads expose power and signals, including `USB5V`, `PIN5V`, `8V-24V`, `UART3`, `UART0`, `UART2/IIC2`, and audio signals.

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
