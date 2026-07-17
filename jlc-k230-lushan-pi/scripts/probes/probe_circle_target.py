# @runtime: canmv
# @route: circle-acceptance
# @requires: camera,lcd

import gc
import os
import time

from media.sensor import *
from media.display import *
from media.media import *


DISPLAY_MODE = "lcd"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DETECT_WIDTH = 400
DETECT_HEIGHT = 240
SENSOR_ID = 2

DISPLAY_CHN = CAM_CHN_ID_0
DETECT_CHN = CAM_CHN_ID_1

SCALE_X = DISPLAY_WIDTH / DETECT_WIDTH
SCALE_Y = DISPLAY_HEIGHT / DETECT_HEIGHT
LCD_CENTER_X = DISPLAY_WIDTH // 2
LCD_CENTER_Y = DISPLAY_HEIGHT // 2

CIRCLE_ROI = (80, 40, 240, 160)
X_STRIDE = 2
Y_STRIDE = 2
CIRCLE_THRESHOLD = 1200
X_MARGIN = 10
Y_MARGIN = 10
R_MARGIN = 10
MIN_RADIUS = 12
MAX_RADIUS = 80
PREFERRED_RADIUS = 34
TRACK_CENTER_WEIGHT = 80
TRACK_RADIUS_WEIGHT = 20
MAX_TRACK_STEP_PIXELS = 100

FRAME_LIMIT = 300
DETECT_EVERY_N_FRAMES = 3
CIRCLE_MISS_HOLD_FRAMES = 6
GC_INTERVAL_FRAMES = 30
PROGRESS_EVERY_N_FRAMES = 60
BIG_JUMP_PIXELS = 100


sensor = None
last_circles = []


def safe_mem_free():
    try:
        return gc.mem_free()
    except Exception:
        return -1


def init_display():
    if DISPLAY_MODE == "lcd":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "hdmi":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    else:
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)


def circle_score(circle):
    try:
        return circle.magnitude()
    except Exception:
        return circle.r()


def abs_int(value):
    if value < 0:
        return -value
    return value


def candidate_rank(item, ref_x, ref_y):
    dx = abs_int(item["lcd_x"] - ref_x)
    dy = abs_int(item["lcd_y"] - ref_y)
    dr = abs_int(item["detect_r"] - PREFERRED_RADIUS)
    return item["score"] - (dx * TRACK_CENTER_WEIGHT) - (dy * TRACK_CENTER_WEIGHT) - (dr * TRACK_RADIUS_WEIGHT)


def sort_circles(found, ref_x, ref_y):
    for i in range(len(found)):
        found[i]["rank"] = candidate_rank(found[i], ref_x, ref_y)
    for i in range(len(found)):
        for j in range(i + 1, len(found)):
            if found[j]["rank"] > found[i]["rank"]:
                found[i], found[j] = found[j], found[i]


def filter_near_reference(found, ref_x, ref_y):
    filtered = []
    for item in found:
        dx = abs_int(item["lcd_x"] - ref_x)
        dy = abs_int(item["lcd_y"] - ref_y)
        if dx + dy <= MAX_TRACK_STEP_PIXELS:
            filtered.append(item)
    return filtered


def detect_circles(img, ref_x, ref_y, has_track):
    found = []
    circles = img.find_circles(roi=CIRCLE_ROI,
                               x_stride=X_STRIDE,
                               y_stride=Y_STRIDE,
                               threshold=CIRCLE_THRESHOLD,
                               x_margin=X_MARGIN,
                               y_margin=Y_MARGIN,
                               r_margin=R_MARGIN)
    for circle in circles:
        radius = circle.r()
        if radius < MIN_RADIUS or radius > MAX_RADIUS:
            continue
        item = {
            "detect_x": circle.x(),
            "detect_y": circle.y(),
            "detect_r": radius,
            "lcd_x": int(circle.x() * SCALE_X),
            "lcd_y": int(circle.y() * SCALE_Y),
            "lcd_r": int(radius * (SCALE_X + SCALE_Y) / 2),
            "score": circle_score(circle),
        }
        found.append(item)
    raw_count = len(found)
    if has_track:
        found = filter_near_reference(found, ref_x, ref_y)
    sort_circles(found, ref_x, ref_y)
    return found, raw_count


def update_range(value, current_min, current_max):
    if current_min < 0 or value < current_min:
        current_min = value
    if current_max < 0 or value > current_max:
        current_max = value
    return current_min, current_max


def draw_overlay(img, circles, fps, frame_id):
    roi_x = int(CIRCLE_ROI[0] * SCALE_X)
    roi_y = int(CIRCLE_ROI[1] * SCALE_Y)
    roi_w = int(CIRCLE_ROI[2] * SCALE_X)
    roi_h = int(CIRCLE_ROI[3] * SCALE_Y)
    img.draw_rectangle((roi_x, roi_y, roi_w, roi_h), color=(40, 40, 255), thickness=2)

    for item in circles[:3]:
        img.draw_circle(item["lcd_x"], item["lcd_y"], item["lcd_r"], color=(0, 255, 0), thickness=3)
        img.draw_cross(item["lcd_x"], item["lcd_y"], color=(255, 0, 0), size=12, thickness=2)

    if circles:
        first = circles[0]
        text = "C:%d,%d R:%d F:%d/%d FPS:%d" % (
            first["lcd_x"], first["lcd_y"], first["lcd_r"], frame_id, FRAME_LIMIT, int(fps))
    else:
        text = "NO CIRCLE F:%d/%d FPS:%d" % (frame_id, FRAME_LIMIT, int(fps))
    img.draw_string_advanced(10, 10, 24, text, color=(255, 0, 0))


def main():
    global sensor
    global last_circles

    mem_start = safe_mem_free()
    detect_runs = 0
    raw_detect_hits = 0
    detect_hits = 0
    overlay_hits = 0
    raw_max = 0
    track_max = 0
    x_min = -1
    x_max = -1
    y_min = -1
    y_max = -1
    r_min = -1
    r_max = -1
    last_x = -1
    last_y = -1
    max_step = 0
    big_jumps = 0
    miss_count = 0

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
    print("CIRCLE_PROBE_START frames=%d detect_every=%d" % (FRAME_LIMIT, DETECT_EVERY_N_FRAMES))

    while frame_id < FRAME_LIMIT:
        os.exitpoint()
        clock.tick()
        display_img = sensor.snapshot(chn=DISPLAY_CHN)

        if frame_id % DETECT_EVERY_N_FRAMES == 0:
            detect_runs += 1
            detect_img = sensor.snapshot(chn=DETECT_CHN)
            has_track = False
            if last_x >= 0 and miss_count < CIRCLE_MISS_HOLD_FRAMES:
                ref_x = last_x
                ref_y = last_y
                has_track = True
            else:
                ref_x = LCD_CENTER_X
                ref_y = LCD_CENTER_Y
            detected_circles, raw_count = detect_circles(detect_img, ref_x, ref_y, has_track)
            if raw_count > 0:
                raw_detect_hits += 1
            if raw_count > raw_max:
                raw_max = raw_count
            if len(detected_circles) > track_max:
                track_max = len(detected_circles)
            if detected_circles:
                detect_hits += 1
                last_circles = detected_circles
                miss_count = 0
                first = detected_circles[0]
                cx = first["lcd_x"]
                cy = first["lcd_y"]
                cr = first["lcd_r"]
                x_min, x_max = update_range(cx, x_min, x_max)
                y_min, y_max = update_range(cy, y_min, y_max)
                r_min, r_max = update_range(cr, r_min, r_max)
                if last_x >= 0:
                    step = abs(cx - last_x) + abs(cy - last_y)
                    if step > max_step:
                        max_step = step
                    if step > BIG_JUMP_PIXELS:
                        big_jumps += 1
                last_x = cx
                last_y = cy
            else:
                miss_count += 1
                if miss_count >= CIRCLE_MISS_HOLD_FRAMES:
                    last_circles = []

        if last_circles:
            overlay_hits += 1

        draw_overlay(display_img, last_circles, clock.fps(), frame_id)
        Display.show_image(display_img)

        frame_id += 1
        if frame_id % PROGRESS_EVERY_N_FRAMES == 0:
            print("CIRCLE_PROGRESS frame=%d raw_hits=%d track_hits=%d overlay=%d fps=%d" % (
                frame_id, raw_detect_hits, detect_hits, overlay_hits, int(clock.fps())))
        if frame_id % GC_INTERVAL_FRAMES == 0:
            gc.collect()

    mem_end = safe_mem_free()
    raw_misses = detect_runs - raw_detect_hits
    track_misses = detect_runs - detect_hits
    print("CIRCLE_PROBE_DONE frames=%d detect_runs=%d raw_hits=%d raw_misses=%d track_hits=%d track_misses=%d overlay_frames=%d raw_max=%d track_max=%d fps=%d x_range=%d..%d y_range=%d..%d r_range=%d..%d max_step=%d big_jumps=%d mem_start=%d mem_end=%d" % (
        frame_id, detect_runs, raw_detect_hits, raw_misses, detect_hits, track_misses, overlay_hits, raw_max, track_max, int(clock.fps()),
        x_min, x_max, y_min, y_max, r_min, r_max, max_step, big_jumps, mem_start, mem_end))


try:
    main()
except KeyboardInterrupt:
    print("CIRCLE_PROBE_STOP user")
except Exception as e:
    print("CIRCLE_PROBE_ERROR", e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    gc.collect()
