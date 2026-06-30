# User Example Patterns

These patterns are distilled from the user's previous working K230 CanMV examples. They are portable and do not depend on the original local file paths.

## Scope

Use this reference to match the user's working-code style and reuse ideas from their prior K230 projects without copying private paths.

## Contents

- Common LCD Preview Pattern
- Button Capture Pattern
- YOLOv5 Detection Pattern
- YOLOv8 COCO Detection Pattern
- Person Keypoint Pattern
- General Style From User Examples

## Common LCD Preview Pattern

For generic camera-to-screen tests, use `assets/contest-template/examples/camera_lcd_preview.py`. The user's prior working examples confirm these practical choices:

- use `Sensor()` for the default CSI camera unless the task needs an explicit sensor id
- use `Sensor.RGB565` for simple LCD preview
- use `img.draw_string_advanced(...)` for large readable on-screen debugging text

## Button Capture Pattern

Use this pattern for collecting training images or contest-site samples:

- map the button pin with `FPIOA` before constructing `Pin`
- use `Pin.IN` with `Pin.PULL_DOWN` if the hardware button is active-high
- keep `last_btn`, `last_press_time`, and `debounce_ms = 300`
- toggle `capture_on` on a rising edge
- save images periodically with `save_interval_ms = 1000`
- create `/data/capture` with `os.mkdir(...)`, ignoring `OSError` if it already exists
- save files as `/data/capture/img_%04d.jpg`
- overlay FPS, capture state, and saved count on the LCD

Example constants:

```python
debounce_ms = 300
save_interval_ms = 1000
save_dir = "/data/capture"
```

Do not reuse any exact button pin unless the user confirms the wiring or schematic.

## YOLOv5 Detection Pattern

Use this pattern for custom small-object detection such as fruit recognition:

- use `from libs.PipeLine import PipeLine`
- use `from libs.YOLO import YOLOv5`
- use `from libs.Utils import *`
- set `display_mode = "lcd"`
- set `rgb888p_size = [640, 360]`
- set `model_input_size = [320, 320]` when the exported model uses 320x320
- set labels inline and ensure order matches the training `data.yaml`
- use `confidence_threshold` and `nms_threshold` constants near the top
- create pipeline with `pl = PipeLine(rgb888p_size=rgb888p_size, display_mode=display_mode)`
- call `pl.create()` and `display_size = pl.get_display_size()`
- construct `YOLOv5(task_type="detect", mode="video", ...)`
- call `yolo.config_preprocess()`
- run inference every 2 frames when FPS is important, reuse `last_res` for drawing each frame
- draw results on `pl.osd_img`, then call `pl.show_image()`
- periodically call `gc.collect()`

Useful baseline thresholds:

```python
confidence_threshold = 0.65
nms_threshold = 0.45
max_boxes_num = 10
```

Use `/data/best.kmodel` as a common simple custom-model path only when the user has not provided a better path.

## YOLOv8 COCO Detection Pattern

Use this pattern for general detection demos:

- use `YOLOv8` from `libs.YOLO`
- use `display_mode = "lcd"`
- use `rgb888p_size = [640, 360]`
- use `model_input_size = [320, 320]`
- use `confidence_threshold = 0.45`, `nms_threshold = 0.45`, `max_boxes_num = 10`
- run inference every 2 frames, store `last_res`, draw every frame
- smooth FPS with an exponential average using `alpha = 0.9`
- draw FPS with `pl.osd_img.draw_string(5, 5, "FPS:%d" % int(fps_avg), color=(255, 0, 0), scale=4)`
- collect garbage every 30 frames

Legacy demo model path seen in prior examples:

```python
kmodel_path = "/data/model/yolov8/yolov8s.kmodel"
```

Use this path only as a legacy/demo convention. For generated project code, ask the user for the actual model path or run the board resource probe before choosing a path.

## Person Keypoint Pattern

Use this pattern for pose/keypoint recognition:

- build a custom app class inheriting from `AIBase`
- use `Ai2d` for pad + resize preprocessing
- set Ai2d dtype with `nn.ai2d_format.NCHW_FMT` and `np.uint8`
- use `aidemo.person_kp_postprocess(...)` for postprocess when matching the official demo
- keep skeleton and keypoint color tables as constants in the app class
- scale keypoint coordinates from `rgb888p_size` to `display_size`
- draw circles for keypoints and lines for skeleton limbs on `pl.osd_img`
- use `display_mode = "lcd"` and `display_size = [800, 480]` for the 3.1-inch screen
- call app `deinit()` and `pl.destroy()` in `finally`

Baseline configuration:

```python
display_mode = "lcd"
rgb888p_size = [1920, 1080]
display_size = [800, 480]
kmodel_path = "/data/model/yolov8/yolov8n-pose.kmodel"
model_input_size = [320, 320]
confidence_threshold = 0.2
nms_threshold = 0.5
```

For K230D or lower-memory situations, reduce `rgb888p_size` such as `[640, 360]` if the model and display pipeline support it.

## General Style From User Examples

- Put model, display, threshold, and path configuration at the top.
- Use `display_mode = "lcd"` as the default for the 3.1-inch screen.
- Use `PipeLine` for AI demos and raw `Sensor`/`Display` for basic camera preview.
- Use frame skipping for heavier YOLO inference.
- Reuse previous result for smoother display when inference is not run every frame.
- Keep on-screen debug text large enough for the 3.1-inch LCD.
- Call `gc.collect()` periodically in AI loops.
- Prefer `try`/`finally` cleanup for camera, display, pipeline, and AI objects.
