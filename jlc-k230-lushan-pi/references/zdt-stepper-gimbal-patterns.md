# ZDT Stepper Gimbal Patterns

Use this reference only when a task involves a confirmed ZDT XS-series second-generation closed-loop stepper motor controlled by the Lushan Pi K230, especially the tested Emm/ZDT free-protocol path with fixed `0x6B` checksum.

For generic gimbals, laser aiming, laser drawing, target following, servo/PWM pan-tilt, MCU-controlled motion, CAN/RS485 modules, or unknown smart motors, read `contest-patterns.md` first and treat this file as non-applicable until the actuator is identified as ZDT-compatible.

For general actuator safety and K230 UART pin rules, read `contest-patterns.md` and `hardware-pin-resource-quickref.md` first.

## Contents

- Scope
- Tested Wiring And Protocol
- Tested Commands
- Motion Results
- Communication Timing
- Recommended Gimbal Control Pattern
- Bring-Up Order
- Safety Rules
- Untested Or Deferred Features

## Scope

This note records board-tested experience from one ZDT XS-series second-generation closed-loop stepper motor controlled by a Lushan Pi K230 over UART2. It is meant for contest-style gimbals, laser pointing, laser tracing, and target-following prototypes only after the actuator has been confirmed as the same ZDT protocol family.

Treat these facts as tested defaults for this user's board and motor, not as universal ZDT or K230 guarantees. Re-verify pin mapping, address, baud rate, supply voltage, firmware mode, and mechanical limits on a new setup.

The tested motor used the ZDT free protocol with fixed `0x6B` checksum. Do not switch to Modbus unless the motor menu or upper-computer tool has been set to Modbus checksum mode.

## Tested Wiring And Protocol

Tested K230 side:

- UART: `UART2`
- FPIOA mapping: `UART2_TXD` on `PIN5/GPIO5`, `UART2_RXD` on `PIN6/GPIO6`
- Baud: `115200`
- Format: `8N1`
- Motor address: `0x01`

Tested motor side:

- TTL wiring uses common ground.
- Motor `R/A/H` connects to controller TX in the tested TTL interpretation.
- Motor `T/B/L` connects to controller RX in the tested TTL interpretation.
- Supply during tests was about `11.8 V`.

Always verify common ground and 3.3 V logic compatibility before connecting K230 GPIO/UART to a motor driver or communication module.

## Tested Commands

The following free-protocol commands returned valid acknowledgments or data on the tested motor.

| Purpose | Command shape | Use |
| --- | --- | --- |
| Enable | `01 F3 AB 01 00 6B` | Lock/enable motor before motion |
| Disable | `01 F3 AB 00 00 6B` | Release motor; use cautiously on a loaded gimbal |
| Stop now | `01 FE 98 00 6B` | Emergency stop and lost-target stop |
| Read position | `01 36 6B` | Position feedback for control/debug |
| Read speed | `01 35 6B` | Stop detection and diagnostics |
| Read target position | `01 33 6B` | Debug active target during motion |
| Read position error | `01 37 6B` | Debug closed-loop settling |
| Read bus voltage | `01 24 6B` | Low-rate power health check |
| Read status flag | `01 3A 6B` | Low-rate health/status check |
| Reset current position to zero | `01 0A 6D 6B` | Define gimbal centered position as zero |
| Ordinary position mode | `FD` packet | Large absolute/relative moves |
| Fast position setup | `F1` packet | Set speed/acc/mode once |
| Fast position delta | `FC` packet | High-rate small relative increments |

For Emm position mode on the tested motor:

- `3200` pulses is one revolution, about `360 deg`.
- `800` pulses is about `90 deg`.
- In `FD`, motion mode `01` means absolute to coordinate zero; motion mode `02` means relative to current real-time position.
- In `F1/FC`, configure speed/acc/mode once with `F1`, then send signed int32 pulse deltas with `FC`.

## Motion Results

Representative board-tested results:

- Speed mode at `20 RPM` for `2.5 s` changed position by about `337.5 deg`, then stopped cleanly.
- Ordinary relative `+90 deg` and `-90 deg` moves reached `+90.000 deg` and `-90.000 deg` deltas in one test.
- Current-position zero reset returned the real-time position to `0.000 deg`.
- Absolute moves reached:
  - `+45 deg` target: about `45.33 deg`
  - `+90 deg` target: about `90.29 deg`
  - `0 deg` target after return: about `-0.20 deg`
- Fast position mode worked for `+10 deg` and `-10 deg` moves, ending within roughly `0.1 deg`.
- Continuous `+1 deg` fast deltas and matching `-1 deg` deltas returned to the starting position within about `0.1 deg`.
- Target overwrite worked: while moving toward `+60 deg`, sending a new `-20 deg` absolute target redirected and ended near `-20.02 deg`.
- Stop command worked; final speed read as `0 RPM`.

## Communication Timing

A pure read stress test ran `80` loops, reading position, speed, status, and bus voltage in each loop:

- Total read commands: `320`
- Failures: `0`
- One feedback read: about `32 ms`
- One full loop of four feedback reads: about `134 ms`
- Bus voltage observed: about `11.78 V` to `11.82 V`

Control implication: do not read every diagnostic value every camera frame. UART feedback is reliable but not free.

Recommended feedback rates:

- Position `0x36`: `10 Hz` to `20 Hz` when needed.
- Speed `0x35`: only for stop detection, debug, or slow supervisory loops.
- Voltage/status `0x24`/`0x3A`: `1 Hz` to `2 Hz`.
- Control deltas `FC`: send at the vision/control period, normally without reading every diagnostic immediately afterward.

## Recommended Gimbal Control Pattern

For laser aiming, laser drawing, or single-axis target following, prefer fast position deltas instead of full `FD` packets in every loop.

Bring-up values that tested well for a gentle single-axis loop:

- Control period: `50 ms` to `70 ms`
- Proportional gain: start around `0.4` to `0.5` after converting visual error to degrees
- Max step: `1 deg` to `2 deg` per update
- Deadband: `0.2 deg` to `0.4 deg`
- Fast position speed: about `50 RPM` to `70 RPM`
- Fast position acceleration: about `40` to `60`

Closed-loop shape:

```text
BOOT:
  configure FPIOA and UART2
  enable motor only after communication responds
  define current centered pose as zero if the mechanism is safe

READY:
  send F1 to configure fast relative-current position mode

TRACK:
  convert pixel error to angle error
  step_deg = clamp(error_deg * kp, -max_step_deg, max_step_deg)
  if abs(error_deg) > deadband:
      send FC signed step pulses

LOST or FAULT:
  send FE 98 00 6B immediately
  do not read or print several diagnostics before stopping
```

The tested single-axis simulation used target sequence `0 -> 15 -> -15 -> 8 -> -8 -> 0`, a `70 ms` control period, `KP=0.48`, `2.2 deg` max step, and `0.25 deg` deadband. Final target errors were roughly `0 deg` to `0.3 deg`, with no lost position reads and all fast-delta commands acknowledged.

## Bring-Up Order

Use this order for a new ZDT gimbal axis:

1. Verify K230 UART2 pin mapping with `scripts/probe_uart2_loopback.py` or user-confirmed wiring.
2. Read motor position with `01 36 6B`; do not move until a valid response is seen.
3. Enable motor and read speed/status.
4. Run a visible low-speed short motion, then stop.
5. Test relative `+90 deg` and `-90 deg` on a free single motor before mounting hardware.
6. Set the intended gimbal center and reset current position to zero.
7. Test absolute small angles such as `+15 deg`, `-15 deg`, and `0 deg`.
8. Test `F1/FC` fast small deltas.
9. Test lost-target stop.
10. Only after mechanical limits and laser safety are handled, integrate visual tracking.

## Safety Rules

- Keep motion disabled until camera detection, LCD/status overlay, and UART communication are stable.
- Always clamp angle, velocity, and per-frame step.
- Add software limits before mounting the motor into a gimbal.
- Do not use high-speed large-angle moves on an unbounded mechanism.
- If the target is lost, send stop immediately; do not read position, target, error, and speed first.
- Do not use `disable` as the normal lost-target action on a loaded gimbal, because the axis may fall or move freely.
- Treat laser enable as a separate safety output; verify motor tracking before enabling the laser.

## Untested Or Deferred Features

The following features should wait until the mechanical gimbal, limit switches, load, and safety setup exist:

- Homing modes and homing-parameter changes.
- Left/right limit switch behavior.
- Heartbeat protection configuration.
- Permanent motor parameter writes.
- Factory reset.
- Firmware switching.
- Multi-axis synchronized movement with actual two-motor hardware.

For two-axis gimbals, test each axis alone first, then test simultaneous small motions with laser disabled.
