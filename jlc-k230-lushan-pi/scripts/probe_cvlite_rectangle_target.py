# @runtime: canmv
# @route: rectangle-acceptance
# @requires: camera,lcd,cv_lite

import gc
import os
import time

from media.sensor import *
from media.display import *
from media.media import *


try:
    import cv_lite
    CV_LITE_OK = True
except Exception as import_error:
    print("RECT_PROBE_IMPORT_ERROR", import_error)
    CV_LITE_OK = False


DISPLAY_MODE = "lcd"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DETECT_WIDTH = 480
DETECT_HEIGHT = 320
SENSOR_ID = 2

DISPLAY_CHN = CAM_CHN_ID_0
DETECT_CHN = CAM_CHN_ID_1

IMAGE_SHAPE = [DETECT_HEIGHT, DETECT_WIDTH]
LCD_CENTER_X = DISPLAY_WIDTH // 2
LCD_CENTER_Y = DISPLAY_HEIGHT // 2
DETECT_CENTER_X = DETECT_WIDTH // 2
DETECT_CENTER_Y = DETECT_HEIGHT // 2

STRICT_CANNY1 = 50
STRICT_CANNY2 = 150
STRICT_EPSILON = 0.04
STRICT_AREA_RATIO = 0.001
STRICT_MAX_ANGLE_COS = 0.3
STRICT_BLUR = 5

FALLBACK_CANNY1 = 30
FALLBACK_CANNY2 = 100
FALLBACK_EPSILON = 0.05
FALLBACK_AREA_RATIO = 0.0005
FALLBACK_MAX_ANGLE_COS = 0.5
FALLBACK_BLUR = 5

MIN_DETECT_AREA = 400
LOST_RESET_FRAMES = 8
FRAME_LIMIT = 300
GC_INTERVAL_FRAMES = 30
PROGRESS_EVERY_N_FRAMES = 60
BIG_JUMP_PIXELS = 60


sensor = None
last_target = None
lost_count = LOST_RESET_FRAMES


def abs_int(value):
    if value < 0:
        return -value
    return value


def safe_mem_free():
    try:
        return gc.mem_free()
    except Exception:
        return -1


def scale_x(x):
    return int(x * DISPLAY_WIDTH // DETECT_WIDTH)


def scale_y(y):
    return int(y * DISPLAY_HEIGHT // DETECT_HEIGHT)


def detect_x(x):
    return int(x * DETECT_WIDTH // DISPLAY_WIDTH)


def detect_y(y):
    return int(y * DETECT_HEIGHT // DISPLAY_HEIGHT)


def init_display():
    if DISPLAY_MODE == "lcd":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "hdmi":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    else:
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)


def detect_rects_strict(img_np):
    return cv_lite.grayscale_find_rectangles_with_corners(IMAGE_SHAPE, img_np, STRICT_CANNY1, STRICT_CANNY2, STRICT_EPSILON, STRICT_AREA_RATIO, STRICT_MAX_ANGLE_COS, STRICT_BLUR)


def detect_rects_fallback(img_np):
    return cv_lite.grayscale_find_rectangles_with_corners(IMAGE_SHAPE, img_np, FALLBACK_CANNY1, FALLBACK_CANNY2, FALLBACK_EPSILON, FALLBACK_AREA_RATIO, FALLBACK_MAX_ANGLE_COS, FALLBACK_BLUR)


def sort_points(points):
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if points[j][0] + points[j][1] < points[i][0] + points[i][1]:
                tmp = points[i]
                points[i] = points[j]
                points[j] = tmp
    top_left = points[0]
    bottom_right = points[3]
    others = [points[1], points[2]]
    if others[0][0] > others[1][0]:
        top_right = others[0]
        bottom_left = others[1]
    else:
        top_right = others[1]
        bottom_left = others[0]
    return [top_left, top_right, bottom_right, bottom_left]


def perspective_center(corners):
    x1 = corners[0][0]
    y1 = corners[0][1]
    x2 = corners[1][0]
    y2 = corners[1][1]
    x3 = corners[2][0]
    y3 = corners[2][1]
    x4 = corners[3][0]
    y4 = corners[3][1]
    denom = (x1 - x3) * (y2 - y4) - (y1 - y3) * (x2 - x4)
    if abs(denom) < 0.0001:
        sx = 0
        sy = 0
        for point in corners:
            sx += point[0]
            sy += point[1]
        return sx // 4, sy // 4
    px = ((x1 * y3 - y1 * x3) * (x2 - x4) - (x1 - x3) * (x2 * y4 - y2 * x4)) / denom
    py = ((x1 * y3 - y1 * x3) * (y2 - y4) - (y1 - y3) * (x2 * y4 - y2 * x4)) / denom
    return int(px), int(py)


def rect_to_target(rect, mode):
    if len(rect) < 12:
        return None
    area = rect[2] * rect[3]
    if area < MIN_DETECT_AREA:
        return None

    corners = []
    i = 4
    while i + 1 < 12:
        corners.append((scale_x(rect[i]), scale_y(rect[i + 1])))
        i += 2
    if len(corners) != 4:
        return None
    corners = sort_points(corners)
    center_x, center_y = perspective_center(corners)
    return {
        "corners": corners,
        "center_x": center_x,
        "center_y": center_y,
        "area": area,
        "mode": mode,
    }


def candidate_score(target):
    if last_target and lost_count < LOST_RESET_FRAMES:
        ref_x = detect_x(last_target["center_x"])
        ref_y = detect_y(last_target["center_y"])
    else:
        ref_x = DETECT_CENTER_X
        ref_y = DETECT_CENTER_Y
    cx = detect_x(target["center_x"])
    cy = detect_y(target["center_y"])
    dx = abs_int(cx - ref_x)
    dy = abs_int(cy - ref_y)
    return target["area"] - (dx * 30) - (dy * 30)


def select_target(rects, mode):
    selected = None
    selected_score = -1000000
    valid_count = 0
    for i in range(len(rects)):
        target = rect_to_target(rects[i], mode)
        if target:
            valid_count += 1
            score = candidate_score(target)
            if score > selected_score:
                selected = target
                selected_score = score
    return selected, valid_count


def find_target(detect_img):
    img_np = detect_img.to_numpy_ref()
    rects = detect_rects_strict(img_np)
    target, valid_count = select_target(rects, 1)
    if target:
        return target, len(rects), valid_count

    rects = detect_rects_fallback(img_np)
    target, valid_count = select_target(rects, 2)
    return target, len(rects), valid_count


def update_range(value, current_min, current_max):
    if current_min < 0 or value < current_min:
        current_min = value
    if current_max < 0 or value > current_max:
        current_max = value
    return current_min, current_max


def draw_target(img, target, rect_count, fps, frame_id):
    img.draw_cross(LCD_CENTER_X, LCD_CENTER_Y, color=(255, 255, 255), size=14, thickness=2)
    if target:
        corners = target["corners"]
        for i in range(4):
            x0 = corners[i][0]
            y0 = corners[i][1]
            x1 = corners[(i + 1) % 4][0]
            y1 = corners[(i + 1) % 4][1]
            img.draw_line(x0, y0, x1, y1, color=(0, 255, 0), thickness=3)
            img.draw_cross(x0, y0, color=(255, 255, 0), size=8, thickness=2)
        cx = target["center_x"]
        cy = target["center_y"]
        img.draw_cross(cx, cy, color=(255, 0, 255), size=22, thickness=3)
        img.draw_circle(cx, cy, 10, color=(255, 0, 255), thickness=2)
        img.draw_string_advanced(8, 8, 24, "RECT:%d M:%d F:%d/%d FPS:%d" % (rect_count, target["mode"], frame_id, FRAME_LIMIT, int(fps)), color=(255, 0, 0))
        img.draw_string_advanced(8, 38, 22, "C:%d,%d E:%d,%d" % (cx, cy, cx - LCD_CENTER_X, cy - LCD_CENTER_Y), color=(255, 0, 255))
    else:
        img.draw_string_advanced(8, 8, 24, "RECT:0 LOST:%d F:%d/%d FPS:%d" % (lost_count, frame_id, FRAME_LIMIT, int(fps)), color=(255, 255, 0))


def main():
    global sensor
    global last_target
    global lost_count

    if not CV_LITE_OK:
        print("RECT_PROBE_DONE frames=0 hits=0 misses=0 strict=0 fallback=0 cv_lite=0")
        return

    mem_start = safe_mem_free()
    hits = 0
    strict_hits = 0
    fallback_hits = 0
    misses = 0
    raw_max = 0
    valid_max = 0
    x_min = -1
    x_max = -1
    y_min = -1
    y_max = -1
    area_min = -1
    area_max = -1
    last_x = -1
    last_y = -1
    max_step = 0
    big_jumps = 0

    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=DISPLAY_CHN)
    sensor.set_pixformat(Sensor.RGB565, chn=DISPLAY_CHN)
    sensor.set_framesize(width=DETECT_WIDTH, height=DETECT_HEIGHT, chn=DETECT_CHN)
    sensor.set_pixformat(Sensor.GRAYSCALE, chn=DETECT_CHN)

    init_display()
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    frame_id = 0
    print("RECT_PROBE_START frames=%d detect=%dx%d display=%dx%d" % (
        FRAME_LIMIT, DETECT_WIDTH, DETECT_HEIGHT, DISPLAY_WIDTH, DISPLAY_HEIGHT))

    while frame_id < FRAME_LIMIT:
        os.exitpoint()
        clock.tick()
        display_img = sensor.snapshot(chn=DISPLAY_CHN)
        detect_img = sensor.snapshot(chn=DETECT_CHN)
        target, rect_count, valid_count = find_target(detect_img)

        if rect_count > raw_max:
            raw_max = rect_count
        if valid_count > valid_max:
            valid_max = valid_count

        if target:
            hits += 1
            if target["mode"] == 1:
                strict_hits += 1
            else:
                fallback_hits += 1
            last_target = target
            lost_count = 0
            cx = target["center_x"]
            cy = target["center_y"]
            area = target["area"]
            x_min, x_max = update_range(cx, x_min, x_max)
            y_min, y_max = update_range(cy, y_min, y_max)
            area_min, area_max = update_range(area, area_min, area_max)
            if last_x >= 0:
                step = abs(cx - last_x) + abs(cy - last_y)
                if step > max_step:
                    max_step = step
                if step > BIG_JUMP_PIXELS:
                    big_jumps += 1
            last_x = cx
            last_y = cy
        else:
            misses += 1
            lost_count += 1
            if lost_count >= LOST_RESET_FRAMES:
                last_target = None

        draw_target(display_img, last_target, rect_count, clock.fps(), frame_id)
        Display.show_image(display_img)

        frame_id += 1
        if frame_id % PROGRESS_EVERY_N_FRAMES == 0:
            print("RECT_PROGRESS frame=%d hits=%d strict=%d fallback=%d misses=%d fps=%d" % (
                frame_id, hits, strict_hits, fallback_hits, misses, int(clock.fps())))
        if frame_id % GC_INTERVAL_FRAMES == 0:
            gc.collect()

    mem_end = safe_mem_free()
    print("RECT_PROBE_DONE frames=%d hits=%d misses=%d strict=%d fallback=%d raw_max=%d valid_max=%d fps=%d x_range=%d..%d y_range=%d..%d area_range=%d..%d max_step=%d big_jumps=%d mem_start=%d mem_end=%d" % (
        frame_id, hits, misses, strict_hits, fallback_hits, raw_max, valid_max, int(clock.fps()),
        x_min, x_max, y_min, y_max, area_min, area_max, max_step, big_jumps, mem_start, mem_end))


try:
    main()
except KeyboardInterrupt:
    print("RECT_PROBE_STOP user")
except Exception as e:
    print("RECT_PROBE_ERROR", e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    gc.collect()
