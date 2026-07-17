# Portable Example and Porting Patterns

Use this reference to extract proven structure from bundled or user-provided K230 examples without importing private paths, stale pin assumptions, or another platform's runtime.

## Scope

This file owns example selection, CanMV porting style, data-collection patterns, and reusable AI-loop structure. Detection algorithms, actuator protocols, deployment, and hardware pin truth remain in their dedicated references.

## Contents

- Choose the Owning Pattern
- Porting Boundaries
- Camera and LCD Style
- Button Data Collection
- AI Pipeline Style
- Scheduling and Cleanup
- Output Boundary
- Porting Checklist

## Choose the Owning Pattern

| Task | Primary reference | Starting asset |
| --- | --- | --- |
| Camera/LCD proof | `references/platform/canmv-workflows.md` | `camera_lcd_preview.py` |
| Rectangle target | `references/vision/contest-2025-rectangle-patterns.md` | `cvlite_rectangle_target_uart_tracker.py` |
| Circle target | `references/vision/circle-detection-patterns.md` | `circle_detect.py` |
| Color/line tracking | `references/control/contest-patterns.md` | `color_line_tracking.py` |
| Threshold calibration | `references/control/contest-patterns.md` | `offline_threshold_tuner.py` |
| Model inference | `references/vision/model-vision-pipeline.md`, then `references/vision/yolo-module-patterns.md` | model-specific project code |
| UART and pins | `references/platform/hardware-pin-resource-quickref.md` | `uart2_loopback.py` |
| Generic centering | `references/control/contest-patterns.md` | `pid_target_centering.py` |

Do not repeat a domain algorithm here. Read the owner reference and use this file only for adapting the source example's structure.

## Porting Boundaries

When reviewing an example from another project:

1. Identify its platform, firmware API, coordinate spaces, model metadata, and actuator protocol.
2. Keep portable ideas such as lifecycle, candidate scoring, frame scheduling, and state transitions.
3. Replace camera, display, filesystem, tensor, and UART APIs with the tested K230 CanMV equivalents.
4. Reconfirm every model path, label order, input size, sensor id, pin, baud rate, and packet format.
5. Remove local absolute paths and provenance-only comments from generated project code.
6. Convert desktop syntax to the conservative CanMV style described in `references/platform/canmv-api-known-issues.md`.

Linux OpenCV, RKNN, OpenMV, and desktop Python examples are design inputs, not directly executable K230 code.

## Camera and LCD Style

Proven raw-camera conventions:

- initialize `Sensor`, `Display`, and `MediaManager` in the order used by the selected template;
- use `Display.ST7701`, `800x480`, and `to_ide=True` for the 3.1-inch LCD;
- use `Sensor.RGB565` for simple preview and a lower-resolution or grayscale detection channel when the algorithm permits;
- name camera, inference, and display coordinate spaces and scale explicitly between them;
- overlay FPS, target state, selected mode, and center/error values with readable text;
- release initialized resources in `finally`.

Use `draw_string_advanced(...)` when large readable LCD text is needed. Do not solve a low-FPS detector by shrinking the final LCD surface; reduce only the processing channel.

## Button Data Collection

A reusable field-capture loop contains:

- FPIOA mapping before constructing `Pin`;
- confirmed input polarity and pull mode;
- edge detection with about `300 ms` debounce;
- a visible capture-enabled state;
- a throttled save interval, often about `1000 ms`;
- monotonically increasing filenames in a known TF-card directory;
- saved-count and write-error overlays.

The built-in `button_capture.py` contains the board-tested USR-key pattern. Treat its pin as a board-specific fact, not a universal button mapping. JPEG encoding and TF-card writes can reduce FPS, so keep collection and final inference programs separate.

## AI Pipeline Style

For firmware-bundled YOLO classes:

- use `PipeLine` for camera/display ownership;
- set `display_mode = "lcd"` and request `display_size = [800, 480]`;
- keep model path, labels, input size, thresholds, and task type at the top;
- call `config_preprocess()` once after model construction;
- run inference on a bounded schedule and draw the most recent result every display frame;
- periodically call `gc.collect()`;
- deinitialize the model and destroy the pipeline in `finally`.

For heavy detection, infer every second frame as an initial performance experiment and retain `last_res` for display. Smooth only the FPS indicator or a separately labeled control center; never present stale model output as a fresh observation without a sequence/timestamp.

For pose/keypoint projects, use an `AIBase` application with `Ai2d` preprocessing, the firmware's matching postprocess helper, and explicit scaling from inference coordinates to LCD coordinates. Copy skeleton topology only when it matches that model's exported keypoint order.

Model defaults found in examples are not project facts. Verify the `.kmodel`, labels, input tensor layout, preprocessing, and postprocessing through `references/vision/model-vision-pipeline.md` before actuator integration.

## Scheduling and Cleanup

Separate loop rates deliberately:

```text
camera/display rate
  != inference rate
  != UART/control rate
  != diagnostic feedback rate
```

Use time-based scheduling when inference FPS changes with scene load. Keep serial logging throttled. A previous result may improve display continuity, but control must reject stale results after a bounded age.

Initialize resource flags before `try`, clean only resources that were created, neutralize confirmed actuator output on ordinary exit, and keep emergency behavior separate from normal cleanup.

## Output Boundary

Example-derived vision code should end with a neutral observation such as:

```text
valid, class_id, confidence, center_x, center_y,
width, height, sequence, timestamp, source_mode
```

Do not copy motor-specific frames from an example unless the user's actuator family, protocol, wiring, signs, limits, and hold behavior are all confirmed. Unknown hardware receives coordinates only.

## Porting Checklist

- The source runtime and target CanMV firmware are identified.
- Camera and LCD initialize at the intended resolutions.
- Every coordinate conversion is explicit and visible on screen.
- Model metadata and result tuple shape are verified, not guessed.
- Pins and packet formats come from the current hardware reference.
- Detection remains stable with actuator output disabled.
- Loop rates, stale-result behavior, and cleanup paths are bounded.
- No local absolute paths or external-project assumptions remain.
