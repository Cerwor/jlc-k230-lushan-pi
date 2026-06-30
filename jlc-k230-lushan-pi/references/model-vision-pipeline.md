# Model Vision Pipeline

Use this file when the user already trains their own model and converts it to `.kmodel`, then wants Codex to package, validate, deploy, or integrate that model on Lushan Pi K230.

This file is intentionally post-conversion focused. Do not turn it into a generic training guide. For board-side YOLO API usage, read `yolo-module-patterns.md`. For uncertain runtime/API signatures, verify through `sources-and-boundaries.md`.

## Scope

Use this reference for self-trained .kmodel handoff, model-package validation, label/input-size contracts, and model-to-control integration gates.

## Contents

- When To Use A Model
- User Artifact Handoff
- Model Package Contract
- Board Bring-Up Gates
- Board-Tested Single-Class YOLO Notes
- Contest Integration Pattern
- Common Failure Modes
- Agent Delivery Checklist

## When To Use A Model

Use a trained model when:

- The target cannot be separated reliably by grayscale/color/geometry thresholds across contest lighting.
- Several visually similar objects require class identity.
- A coarse ROI from the model can simplify a fragile classical-vision step.
- Target appearance changes with pose, distance, or background.

Prefer classical vision when:

- The target is a high-contrast geometric mark such as black tape on white paper.
- Exact center, edge, corner, angle, or radius matters more than semantic classification.
- A stable threshold, corner, circle, blob, or line rule is available.

For control-class contest tasks, prefer a hybrid when possible:

1. Use the model for coarse object/ROI selection.
2. Use classical vision inside the ROI for precise center, corner, line, circle, or angle.
3. Use temporal tracking to hold the target through short misses.
4. Send only stable coordinates or signed error values to actuators.

## User Artifact Handoff

Assume the user owns training and `.kmodel` conversion. Before writing final board code, ask for:

- `.kmodel` file.
- `labels.txt` or exact label order.
- Task type: `classify`, `detect`, or `segment`.
- YOLO wrapper class if applicable: `YOLOv5`, `YOLOv8`, `YOLO11`, or `custom`.
- Model input size, such as `[224, 224]`, `[320, 320]`, or `[640, 640]`.
- Intended board path, such as `/sdcard/models/target.kmodel`.
- Confidence/NMS/mask thresholds used during validation.
- Preprocess notes that affect board code: RGB/BGR, resize/letterbox, normalization, CHW/HWC.
- Conversion notes or logs if the `.kmodel` has not yet loaded successfully on a K230.

Do not fabricate model paths, labels, input size, conversion success, or output tuple shape. If any of those are unknown, deliver a scaffold that marks the missing artifact clearly.

## Model Package Contract

Package the user's post-conversion artifacts as one folder:

```text
model-package/
  model_manifest.json
  labels.txt
  target.kmodel
  conversion-log.txt      optional
  sample-test.jpg         optional but useful
```

Use `assets/model-package/model_manifest.example.json` as the starting shape.

Required manifest fields:

- `model_name`: short project name.
- `task_type`: `classify`, `detect`, or `segment`.
- `yolo_class`: `YOLOv5`, `YOLOv8`, `YOLO11`, or `custom`.
- `kmodel_file`: local file name inside the package.
- `labels_file`: local file name inside the package.
- `model_input_size`: two positive integers.
- `board_kmodel_path`: intended absolute board path.

Recommended manifest fields:

- `rgb888p_size`: camera/PipeLine inference frame size.
- `display_size`: usually `[800, 480]` for the 3.1-inch LCD.
- `confidence_threshold`, `nms_threshold`, `mask_threshold`.
- `max_boxes_num`.
- `preprocess`: short note for color, resize, normalization, and layout.
- `postprocess`: wrapper/postprocess notes, including anchors/strides for custom code.
- `validation`: still-image, video/LCD, and field-case notes.

Keep label order in `labels.txt` as the single source of truth. Only add inline manifest `labels` if a project needs an extra consistency check.

Run the host-side check before board integration:

```powershell
python ".\jlc-k230-lushan-pi\scripts\check_model_package.py" ".\model-package"
```

The checker verifies file presence, manifest fields, label consistency when inline labels are present, model input size, threshold ranges, and package-relative local file paths.

## Board Bring-Up Gates

Use these gates before control integration:

1. Runtime gate: run `tools/test.ps1 -Board -Vision yolo -Port COM14` or `scripts/probe_yolo_runtime.py`.
2. Package gate: run `scripts/check_model_package.py` on the host-side model package.
3. File gate: copy or place the `.kmodel` at the manifest board path only when the user explicitly asks to deploy.
4. Still-image gate: run one known image through the `.kmodel`; verify labels, scores, boxes/masks, and draw coordinates.
5. Video gate: run camera plus 3.1-inch LCD with actuator outputs disabled.
6. Result-structure gate: print or draw parsed detection fields for a few frames; do not assume output tuple shape.
7. FPS gate: measure with final input size and display mode; decide whether to skip frames or reuse last result.
8. Field gate: test normal, bright, shadow, dim, and distractor scenes.
9. Control gate: only after stable overlay, enable UART/control output with clamps and target-lost behavior.

For the 3.1-inch LCD, keep `display_mode = "lcd"` and `display_size = [800, 480]`. If using `PipeLine`, run inference at a smaller `rgb888p_size` when FPS matters.

## Board-Tested Single-Class YOLO Notes

The current user-trained contest detector baseline is a single-class YOLOv8 detect model:

- Board file: `/sdcard/best.kmodel`
- Size observed on TF card: `3347424` bytes
- Label order: `["Rec"]`
- Input size: `[320, 320]`
- Camera/PipeLine inference size: `rgb888p_size = [320, 320]`
- Display: 3.1-inch LCD, `display_mode = "lcd"`, `display_size = [800, 480]`

For this tested YOLOv8 wrapper path, detection results were observed as:

```text
res[0] = boxes
res[1] = class ids
res[2] = scores
box = [x, y, w, h]
center = (x + w / 2, y + h / 2)
```

Do not assume this tuple shape for another model or firmware. Keep the result-structure gate in the first board run and draw/log a few parsed detections before enabling control output.

Board-tested video gates for this model:

- Fixed target probe: `300/300` hits, about `22.6 FPS`, score around `0.54` in the tested scene.
- Moving target probe: `1168/1200` hits, about `26.9 FPS`, center range about `x=83..739`, `y=41..466`, score range about `0.25..0.54`, `8` short lost segments.

Control implication: the model is stable enough to drive a gimbal, but final code should keep `LOST_STOP -> REACQUIRE -> TRACK`, candidate filtering, and a confidence threshold that can be lowered for dim scenes. A good starting `CONTROL_SCORE_THRESH` for this tested model is around `0.35`; re-test at the contest venue.

## Contest Integration Pattern

For a detector used in a control loop:

- Keep constants at the top: model path, labels, thresholds, input size, display size, UART packet format, and lost-target timeout.
- Choose a target candidate by class, confidence, area, and distance to previous center.
- Use a short confirmation count before declaring target acquired.
- Hold the last good target for a small number of frames.
- Output `lost` or neutral control when the target is missing too long.
- Overlay class, confidence, center, error from screen center, FPS, and control state.
- Throttle UART output independently from LCD FPS.
- For precise aiming, refine inside the model ROI using rectangle/circle/line/blob logic when possible.

For multi-object tasks:

- Keep a stable class-to-action table.
- Reject classes that are not part of the contest rule.
- Draw all detections lightly, but highlight only the selected target.

## Common Failure Modes

- Label order mismatch: boxes draw with wrong names; fix `labels.txt`.
- Input size mismatch: model loads but detections are nonsense or shifted; confirm `model_input_size`.
- Preprocessing mismatch: RGB/BGR, normalization, letterbox, or CHW/HWC differs from training/export.
- Threshold too high: no detections in dim light; lower confidence or collect field samples.
- Threshold too low: distractors trigger; use negatives, class filters, ROI, and temporal filters.
- Conversion/runtime mismatch: `.kmodel` fails to load or outputs invalid tensors; match conversion toolchain to firmware and keep logs.
- Official example path mismatch: probe board resources before assuming `/data/...`.
- HDMI default on 3.1-inch LCD: change `display_mode` to `lcd` and use `display_size = [800, 480]`.
- FPS too low: reduce input size, skip frames, use last-result hold, or use the model only for coarse ROI.

## Agent Delivery Checklist

When asked to build a K230 model-vision solution, deliver or request:

- Converted `.kmodel`, exact labels, input size, task type, and wrapper class.
- A model package with manifest and `labels.txt`.
- A host-side `check_model_package.py` result.
- A board-side still-image test path.
- A board-side video/LCD test path.
- A control integration plan with outputs disabled first.
- A field re-test plan for normal, bright, shadow, dim, and distractor scenes.
