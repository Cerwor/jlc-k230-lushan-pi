import gc
import os
import time

from media.sensor import *
from media.display import *
from media.media import *


DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DETECT_WIDTH = 400
DETECT_HEIGHT = 240
SENSOR_ID = 2

DISPLAY_CHN = CAM_CHN_ID_0
DETECT_CHN = CAM_CHN_ID_1

SCALE_X = DISPLAY_WIDTH / DETECT_WIDTH
SCALE_Y = DISPLAY_HEIGHT / DETECT_HEIGHT

COLOR_THRESHOLDS = [(41, 57, 31, 83, 13, 71)]
BLOB_ROI = (0, 0, DETECT_WIDTH, DETECT_HEIGHT)
LINE_ROI_HALF = (0, 0, DETECT_WIDTH // 2, DETECT_HEIGHT // 2)
BLOB_PIXELS_THRESHOLD = 300
LINE_MIN_LENGTH = 35
DETECT_EVERY_N_FRAMES = 2
GC_INTERVAL_FRAMES = 30


sensor = None
last_blobs = []
last_lines = []


def scale_x(x):
    return int(x * SCALE_X)


def scale_y(y):
    return int(y * SCALE_Y)


def detect_features(img):
    packed_blobs = []
    blobs = img.find_blobs(COLOR_THRESHOLDS, False, BLOB_ROI,
                           x_stride=5, y_stride=5,
                           pixels_threshold=BLOB_PIXELS_THRESHOLD,
                           margin=True)
    for blob in blobs:
        packed_blobs.append({
            "x": scale_x(blob.x()),
            "y": scale_y(blob.y()),
            "w": scale_x(blob.w()),
            "h": scale_y(blob.h()),
            "cx": scale_x(blob.cx()),
            "cy": scale_y(blob.cy()),
        })

    packed_lines = []
    line_img = img.to_rgb565(copy=True)
    line_img.midpoint_pool(2, 2)
    lines = line_img.find_line_segments(LINE_ROI_HALF, 15, 15)
    for line in lines:
        if line.length() > LINE_MIN_LENGTH:
            packed_lines.append({
                "x1": scale_x(line.x1() * 2),
                "y1": scale_y(line.y1() * 2),
                "x2": scale_x(line.x2() * 2),
                "y2": scale_y(line.y2() * 2),
            })

    return packed_blobs, packed_lines


def draw_features(img, blobs, lines, fps):
    for blob in blobs:
        img.draw_rectangle(blob["x"], blob["y"], blob["w"], blob["h"],
                           color=(0, 255, 0), thickness=3)
        img.draw_cross(blob["cx"], blob["cy"], color=(255, 255, 0), size=10, thickness=2)

    for line in lines:
        img.draw_line(line["x1"], line["y1"], line["x2"], line["y2"],
                      color=(255, 0, 0), thickness=3)

    img.draw_string_advanced(10, 10, 28,
                             "B:%d L:%d FPS:%d" % (len(blobs), len(lines), int(fps)),
                             color=(255, 0, 0))


try:
    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=DISPLAY_CHN)
    sensor.set_pixformat(Sensor.RGB565, chn=DISPLAY_CHN)
    sensor.set_framesize(width=DETECT_WIDTH, height=DETECT_HEIGHT, chn=DETECT_CHN)
    sensor.set_pixformat(Sensor.RGB565, chn=DETECT_CHN)

    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    frame_id = 0
    print("color line tracking dual-channel start")

    while True:
        os.exitpoint()
        clock.tick()
        display_img = sensor.snapshot(chn=DISPLAY_CHN)

        if frame_id % DETECT_EVERY_N_FRAMES == 0:
            detect_img = sensor.snapshot(chn=DETECT_CHN)
            last_blobs, last_lines = detect_features(detect_img)

        draw_features(display_img, last_blobs, last_lines, clock.fps())
        Display.show_image(display_img)

        frame_id += 1
        if frame_id % GC_INTERVAL_FRAMES == 0:
            gc.collect()

except KeyboardInterrupt:
    print("user stopped")
except Exception as e:
    print("error:", e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    gc.collect()
