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
- Tested Two-Axis Vision Gimbal Pattern
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
- Single-axis tests used address `0x01`; the tested two-axis gimbal used yaw address `0x01` and pitch address `0x02`.

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
- ACK reads can occasionally miss even when the motor executes the command. Treat isolated missed ACKs on `enable` or `FC` as a warning, not an immediate fault; require repeated misses before entering communication fault, and always retry `stop` several times.

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

## Tested Two-Axis Vision Gimbal Pattern

The current two-axis ZDT gimbal has been board-tested with a Lushan Pi K230 camera mounted on the gimbal:

- Yaw motor: address `0x01`.
- Pitch motor: address `0x02`.
- K230 UART2: `PIN5/GPIO5` as `UART2_TXD`, `PIN6/GPIO6` as `UART2_RXD`, `115200 8N1`.
- The recommended control path is camera/LCD + `cv_lite` rectangle target center + bounded `F1/FC` relative-current deltas.
- Use `F1` once per axis after enabling; then send small signed `FC` deltas during tracking.
- For the tested camera orientation, target-center control signs were:
  - `yaw_step = clamp(err_x * PIXEL_TO_DEG * -1.0, ...)`
  - `pitch_step = clamp(err_y * PIXEL_TO_DEG * +1.0, ...)`
  where `err_x = target_x - 400` and `err_y = target_y - 240` on the `800x480` LCD.
- Typical conservative bring-up values:
  - `FAST_RPM = 25`
  - `FAST_ACC = 20`
  - `CONTROL_EVERY_N_FRAMES = 5`
  - `PIXEL_TO_DEG = 0.006`
  - `MAX_STEP_DEG = 0.25` to `0.45`
  - short test `MAX_TOTAL_AXIS_DEG = 3` to `4`
  - wider moving-target test `MAX_TOTAL_AXIS_DEG = 6`
  - `DEADBAND_X_PX` and `DEADBAND_Y_PX` around `20` to `36`
- Require a vision precheck before enabling motors. A tested shape was `36` precheck frames with at least `24` valid rectangle hits.
- On target loss, stop first. A tested path sent `FE 98 00 6B` after `3` consecutive missed frames and then suppressed further motion commands.
- Do not use a black-blob detector as the final gimbal input in cluttered scenes; it can lock onto a computer screen or other dark regions. Use `cv_lite` rectangle corners or a model-assisted ROI before enabling ZDT motion.
- Full tracking mode should remove only the short-test cumulative-angle limiter. Keep per-command `MAX_STEP_DEG`, target-loss stop, startup precheck, final stop, and real mechanical soft limits.

Board-tested closed-loop observations:

- Camera/LCD plus UART2 motor control can run together. A camera+gimbal coexistence smoke test completed with all motion commands acknowledged and about `36 FPS`.
- With `cv_lite` rectangle input, a black rectangle target was tracked at about `39` to `49 FPS` during ZDT control tests and about `62` to `63 FPS` in vision-only probes.
- Small black object clutter did not steal the target when selecting by valid rectangle geometry and area: the main target stayed as candidate `#1`, while a small object appeared as candidate `#2`.
- A 300-frame cluttered-scene vision probe reached `298/300` hits, `big_jumps=0`, and center ranges around `x=427..432`, `y=213..219`.
- Four-direction tests confirmed the above sign mapping:
  - target on left: x moved from about `224` to `272`, yaw total `+4 deg`;
  - target on right: x moved from about `670` to `639`, yaw total `-4 deg`;
  - target above center: y moved from about `128` to `170`, pitch total `-4 deg`;
  - target below center: y moved from about `329` to `298`, pitch total `+4 deg`.
- A moving-target test with clutter kept `260/260` target hits, no lost stop, and `63/63` motion ACKs; pitch reached the configured `6 deg` test limit.
- A long closed-loop run with a fixed or slowly moved target completed `3600` frames with `3597` hits, `3` misses, about `60 FPS`, `54/54` motion ACKs, `max_step=11`, `big_jumps=0`, yaw total `-6.000 deg`, and pitch total `+4.426 deg`.
- A full tracking run with the short-test cumulative limiter disabled completed `7200` frames at about `50 FPS`, with `7089` hits, `111` misses, `486/490` motion ACKs, `ack_miss=4`, target center range `x=154..519`, `y=140..324`, yaw total `-18.654 deg`, and pitch total `+2.382 deg`. It correctly entered lost-stop at frame `4193` after `3` consecutive missed detections.

For final contest code, replace short-test total motion limits with real soft limits based on the actual gimbal mechanics. Keep software limits in axis angle space and keep an immediate repeated stop path for `LOST`, `FAULT`, and `KeyboardInterrupt`.

If the task requires continuous competition operation, do not leave the system permanently stopped after one target-loss event. Use a small state machine:

```text
TRACK:
  target valid; send bounded FC deltas

LOST_STOP:
  after consecutive misses, send stop several times and suppress deltas

REACQUIRE:
  keep detecting with motors stopped
  require N stable rectangle hits before motion resumes

TRACK:
  re-enable or re-arm only after reacquire passes
```

This keeps the tested safety behavior while allowing the gimbal to resume after the target reappears.

### Self-Trained YOLO Target Gimbal Notes

The same two-axis ZDT gimbal was also tested with the user-trained single-class YOLOv8 model described in `model-vision-pipeline.md`:

- Model path: `/sdcard/best.kmodel`
- Label: `Rec`
- Input/PipeLine size: `320x320`
- YOLO center source: `box = [x, y, w, h]`, center from `x + w/2`, `y + h/2`
- Direction signs remained correct for the mounted camera:
  - `yaw_step = clamp(err_x * PIXEL_TO_DEG * -1.0, ...)`
  - `pitch_step = clamp(err_y * PIXEL_TO_DEG * +1.0, ...)`

Use this bring-up sequence for a model-driven gimbal:

1. Run YOLO video-only until model path, label order, tuple shape, center coordinates, score range, and FPS are known.
2. Move the target by hand with motors disabled; verify no large center jumps and no long lost segments.
3. Enable ZDT control with small FC deltas and real software angle limits.
4. For tuning or suspected non-motion, read motor position before and after the test; command totals alone do not prove the axis moved.

Board-tested YOLO + ZDT observations:

- Conservative `FC` loop: `FAST_RPM=30`, `FAST_ACC=25`, `CONTROL_EVERY_N_FRAMES=4`, `MAX_STEP_DEG=0.40` tracked safely but could hit a small `12 deg` yaw test limit before reaching the target.
- Wider safe test: `FAST_RPM=30`, `FAST_ACC=25`, wider `25 deg` limits, about `21 FPS`, `438/438` command ACKs, and only `12` misses in `1500` frames.
- Smooth sampled-ACK test: `FAST_RPM=45`, `FAST_ACC=35`, `CONTROL_PERIOD_MS=70`, `MAX_STEP_DEG=0.25`, `SMOOTH_ALPHA=0.30`, `FC_ACK_SAMPLE_EVERY=20` improved loop FPS to about `30` and felt smoother than waiting for every FC ACK, but was slower to converge.
- Medium sampled-ACK test: `FAST_RPM=55`, `FAST_ACC=45`, `CONTROL_PERIOD_MS=55`, `MAX_STEP_DEG=0.35`, `SMOOTH_ALPHA=0.35` sent more motion, but commanded totals alone were not enough to judge actual tracking.
- Visible validation test: `FAST_RPM=60`, `FAST_ACC=50`, `CONTROL_PERIOD_MS=65`, `MAX_STEP_DEG=0.75`, `SMOOTH_ALPHA=0.45`, every-FC ACK, and position reads proved real movement: commanded yaw about `25.97 deg`, measured yaw delta about `23.61 deg`; commanded pitch about `1.90 deg`, measured pitch delta about `3.09 deg`.

For final model tracking, start from a middle ground instead of the most aggressive validation mode:

```text
FAST_RPM = 55
FAST_ACC = 45
CONTROL_PERIOD_MS = 55 to 65
MAX_STEP_DEG = 0.35 to 0.60
MAX_TOTAL_AXIS_DEG = 30 to 45, then replace with real mechanical soft limits
SMOOTH_ALPHA = 0.35 to 0.45
CONTROL_SCORE_THRESH = 0.35, then field-tune
FC_ACK_SAMPLE_EVERY = 10 to 20
```

Important control lessons:

- Waiting for every `FC` ACK lowers FPS and can make motion feel stepped. For final smooth operation, write most `FC` packets directly and sample ACK/status periodically.
- Sampled ACK counts are optimistic unless stale UART bytes are drained. When diagnosing motion, temporarily wait for every `FC` ACK and read `0x36` position before/after.
- Use a low-pass target center: `smooth = smooth * (1 - alpha) + raw * alpha`.
- Use a time-based control period instead of frame modulo, because YOLO FPS can change with target scene and display load.
- Keep stop/setup/enable commands ACK-checked even when FC deltas use sampled ACK.
- If the user says the gimbal barely moves but direction is correct, increase per-step/period/gain only after position feedback confirms whether the motor physically followed the commands.

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
11. For vision tracking, run vision-only candidate labeling first, then enable motors only after the displayed target is confirmed to be the intended object.

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
