# YOLO Module Patterns

These notes distill the official LCKFB/JLC K230 CanMV YOLO module API page. Use them when writing YOLOv5, YOLOv8, YOLO11, classification, detection, or segmentation examples.

Official API source: https://wiki.lckfb.com/zh-hans/lushan-pi-k230/api/aidemo/yolo_module_api.html

For self-trained models that the user converts to `.kmodel`, first use `references/vision/model-vision-pipeline.md` to check the model package, labels, input size, board paths, and validation gates. Then use this file for board-side YOLO code.

For failures, use `references/platform/troubleshooting.md#yolo-kmodel-or-ai-problems`. For firmware/API drift, use `references/maintenance/maintenance.md#update-policy`.

For final contest scripts, also use `references/platform/canmv-api-known-issues.md#conservative-syntax-and-validation`; desktop Python syntax compatibility does not guarantee CanMV IDE compatibility.

## Scope

Use this reference for YOLO/KModel/PipeLine lifecycle, official example adaptation, model paths, and 3.1-inch LCD display changes.

## Contents

- Supported Classes and Tasks
- Required User Inputs
- Constructor Parameters
- Standard Method Flow
- Result Semantics
- Still Image Mode
- Video Mode with PipeLine
- Family-Specific Defaults From Official Examples
- Contest-Oriented YOLO Guidance
- Non-K230 YOLO/RKNN Samples
- Board-Proven YOLO Smoke Results

## Supported Classes and Tasks

The official module exposes:

- `YOLOv5`
- `YOLOv8`
- `YOLO11`

All three classes follow the same high-level pattern and support:

- `task_type="classify"`
- `task_type="detect"`
- `task_type="segment"`

All three support:

- `mode="image"` for still-image inference
- `mode="video"` for camera/PipeLine video inference

## Required User Inputs

Before writing final YOLO code, collect or infer:

- YOLO family: `YOLOv5`, `YOLOv8`, or `YOLO11`
- task type: `classify`, `detect`, or `segment`
- mode: `image` or `video`
- `.kmodel` path on the board, usually under `/data/...`
- labels list in the same order as the trained/exported model
- `model_input_size`, such as `[224, 224]`, `[320, 320]`, or `[640, 640]`
- `rgb888p_size`, the frame size entering inference
- display mode and `display_size` for video mode
- thresholds: confidence, NMS, mask when segmentation is used
- max output boxes for detection/segmentation

Do not silently invent labels or model sizes for project code. For demos, clearly mark demo defaults.

## Constructor Parameters

The common constructor shape is:

```python
yolo = YOLOv8(
    task_type="detect",
    mode="video",
    kmodel_path=kmodel_path,
    labels=labels,
    rgb888p_size=rgb888p_size,
    model_input_size=model_input_size,
    display_size=display_size,
    conf_thresh=confidence_threshold,
    nms_thresh=nms_threshold,
    mask_thresh=mask_threshold,
    max_boxes_num=max_boxes_num,
    debug_mode=0,
)
```

Parameter meanings:

- `task_type`: `classify`, `detect`, or `segment`
- `mode`: `image` or `video`
- `kmodel_path`: path to `.kmodel` copied to the board
- `labels`: list of class names
- `rgb888p_size`: inference frame resolution, such as `[1920,1080]`, `[1280,720]`, or `[640,640]`
- `model_input_size`: training/export input size, such as `[224,224]`, `[320,320]`, or `[640,640]`
- `display_size`: required for video display; commonly `[1920,1080]` for HDMI or `[800,480]` for LCD
- `conf_thresh`: confidence threshold in `[0,1]`
- `nms_thresh`: NMS threshold in `[0,1]`, required for detection and segmentation
- `mask_thresh`: segmentation mask binary threshold in `[0,1]`
- `max_boxes_num`: maximum boxes returned per frame
- `debug_mode`: `0` disables timing, `1` enables timing

Only include `mask_thresh` for segmentation tasks unless keeping one shared template is more convenient.

## Standard Method Flow

Use this exact lifecycle:

1. Construct the YOLO object.
2. Call `yolo.config_preprocess()`.
3. Get an image/frame.
4. Call `res = yolo.run(img)`.
5. Call `yolo.draw_result(res, img_ori_or_pl_osd_img)`.
6. Call `gc.collect()` periodically or after still-image inference.
7. Call `yolo.deinit()` in `finally`.

For video mode with `PipeLine`, also call `pl.destroy()` in `finally`.

## Result Semantics

`run(img)` returns different result structures by task:

- classification: class index and score
- detection: list of box position, score, and class index
- segmentation: mask result plus box position, score, and class index

Pass the returned result directly to `draw_result(...)` unless the user explicitly needs custom decision logic. For contest control, parse the detection list only after verifying the exact returned structure on the user's firmware/model.

## Still Image Mode

Official still-image examples read an image, convert to RGB888, then convert HWC to CHW before inference:

```python
import image

def read_img(img_path):
    img_data = image.Image(img_path)
    img_data_rgb888 = img_data.to_rgb888()
    img_hwc = img_data_rgb888.to_numpy_ref()
    shape = img_hwc.shape
    img_tmp = img_hwc.reshape((shape[0] * shape[1], shape[2]))
    img_tmp_trans = img_tmp.transpose()
    img_res = img_tmp_trans.copy()
    img_return = img_res.reshape((shape[2], shape[0], shape[1]))
    return img_return, img_data_rgb888
```

Use still-image mode first when validating a new `.kmodel` because it separates model issues from camera/display issues.

## Video Mode with PipeLine

Official video examples use:

```python
from libs.PipeLine import PipeLine, ScopedTiming
from libs.YOLO import YOLOv8
import os, sys, gc

display_mode = "lcd"
rgb888p_size = [640, 360]
display_size = [800, 480]

pl = PipeLine(rgb888p_size=rgb888p_size, display_size=display_size, display_mode=display_mode)
pl.create()

yolo = YOLOv8(
    task_type="detect",
    mode="video",
    kmodel_path=kmodel_path,
    labels=labels,
    rgb888p_size=rgb888p_size,
    model_input_size=model_input_size,
    display_size=display_size,
    conf_thresh=confidence_threshold,
    nms_thresh=nms_threshold,
    max_boxes_num=max_boxes_num,
    debug_mode=0,
)
yolo.config_preprocess()

try:
    while True:
        os.exitpoint()
        with ScopedTiming("total", 1):
            img = pl.get_frame()
            res = yolo.run(img)
            yolo.draw_result(res, pl.osd_img)
            pl.show_image()
            gc.collect()
except Exception as e:
    print("error:", e)
finally:
    yolo.deinit()
    pl.destroy()
```

For this user's 3.1-inch LCD workflow, prefer `display_mode = "lcd"` and `display_size = [800, 480]`. The official examples often default to HDMI; adapt them to LCD unless the user asks for HDMI.

## Family-Specific Defaults From Official Examples

YOLOv5 detection demo:

```python
from libs.YOLO import YOLOv5

kmodel_path = "/data/yolo_kmodels/det_yolov5n_320.kmodel"
labels = ["apple", "banana", "orange"]
model_input_size = [320, 320]
confidence_threshold = 0.5
nms_threshold = 0.45
max_boxes_num = 50
```

YOLOv8 classification demo:

```python
from libs.YOLO import YOLOv8

kmodel_path = "/data/yolo_kmodels/cls_yolov8n_224.kmodel"
labels = ["apple", "banana", "orange"]
model_input_size = [224, 224]
confidence_threshold = 0.5
```

YOLO11 segmentation demo:

```python
from libs.YOLO import YOLO11

kmodel_path = "/data/yolo_kmodels/seg_yolo11n_320.kmodel"
labels = ["apple", "banana", "orange"]
model_input_size = [320, 320]
confidence_threshold = 0.5
nms_threshold = 0.45
mask_threshold = 0.5
max_boxes_num = 50
```

Treat these as demo defaults, not project facts.

## Contest-Oriented YOLO Guidance

- From the folder containing `SKILL.md`, start with `python .\scripts\run_board_probe.py --vision yolo --port COM14` before assuming imports, model paths, or official example layout.
- Validate the `.kmodel` in still-image mode first.
- Then run video mode with camera and LCD but no actuator output.
- Then parse results and enable decision/control logic.
- Keep thresholds, labels, model path, input size, display mode, and frame size as top-level constants.
- Use frame skipping and last-result reuse when FPS matters.
- Overlay FPS, target label, confidence, center point, and control state.
- Keep `debug_mode=0` for normal runs; use `debug_mode=1` or `ScopedTiming` while profiling.
- Call `gc.collect()` regularly in video loops.
- Always release YOLO and pipeline resources in `finally`.

`ACCEPT_YOLO status=pass` from the repository test means the runtime imports and bundled YOLO classes are available, and the board scan found model/example resources. It does not prove the user's trained model has correct labels, input size, or post-processing.

## Non-K230 YOLO/RKNN Samples

Linux/OpenCV/RKNN examples for RK3576 or other Rockchip boards are not directly portable to Lushan Pi K230 CanMV:

- `.rknn` model files run through RKNN runtime, not K230 KPU.
- `rknn.api.RKNN`, OpenCV camera capture, Flask/MJPEG streaming, and Linux serial paths are platform-specific.
- ONNX files are source artifacts for conversion; they are not runnable by CanMV directly. Convert and validate a `.kmodel` for K230 instead.

Useful ideas to keep from those samples:

- Prefer one named target class for contest tracking, such as a ball, cap, block, or marker.
- When multiple boxes pass threshold, score candidates by confidence plus distance to the frame center or previous target.
- Send signed error from frame center for pan/tilt control instead of only absolute box coordinates.
- Throttle UART output separately from display FPS.
- Overlay target state, serial state, FPS, and center/error values before enabling actuators.

## Board-Proven YOLO Smoke Results

The reference firmware has successfully imported `nncase_runtime`, `aicube`, `PipeLine`, and the bundled YOLOv5/YOLOv8/YOLO11 classes. Official examples and models were also found under `/sdcard/examples/`, and both still-image and LCD video YOLOv8 smoke tests completed.

Treat this only as a runtime capability baseline. It does not validate a user's labels, model input, preprocessing, result tuple, or postprocessing. Exact resource counts and timing telemetry belong in the repository `docs/BOARD_TEST_LOG.md`.

## Board-Proven YOLOv8 LCD Launcher

On the tested board, `/data/model/yolov8/yolov8s.kmodel` did not exist. The SD-card image instead contained official examples and models under `/sdcard/examples/`, including:

- `/sdcard/examples/05-AI-Demo/object_detect_yolov8n.py`
- `/sdcard/examples/kmodel/yolov8n_seg_320.kmodel`
- `/sdcard/examples/kmodel/yolov8n-pose.kmodel`

Before assuming a model path, run `scripts/run_board_probe.py --vision resources` or otherwise list board paths.

The official `object_detect_yolov8n.py` may default to HDMI and fail on the 3.1-inch LCD with `RuntimeError: init panel failed`. Use `assets/contest-template/examples/model/yolov8_lcd_official_launcher.py` rather than duplicating its runtime-patching code here.

The launcher must keep these fail-fast invariants:

- verify that the official example file exists;
- require at least one known HDMI assignment to be replaced;
- reject the launch if a known HDMI `display_mode` assignment remains;
- report source-layout drift instead of silently executing the unchanged HDMI example.

The asset was board-tested with a live LCD preview. Revalidate it whenever the official SD-card example changes, because runtime source replacement is intentionally a compatibility workaround rather than a stable API.
