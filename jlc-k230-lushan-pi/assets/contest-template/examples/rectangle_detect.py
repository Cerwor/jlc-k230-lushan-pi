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

RECT_ROI = (0, 0, DETECT_WIDTH, DETECT_HEIGHT)
GAMMA = 3
BINARY_THRESHOLD = (160, 255)
RECT_THRESHOLD = 2500
FALLBACK_RECT_THRESHOLD = 5000
MIN_RECT_AREA = 100
MAX_DRAW_RECTS = 6
DETECT_EVERY_N_FRAMES = 2
RECT_MISS_HOLD_FRAMES = 6
GC_INTERVAL_FRAMES = 30


sensor = None
last_rects = []


def init_display():
    if DISPLAY_MODE == "lcd":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "hdmi":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    else:
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)


def rect_area(rect_tuple):
    return rect_tuple[2] * rect_tuple[3]


def scale_point(point):
    return int(point[0] * SCALE_X), int(point[1] * SCALE_Y)


def pack_rect(rect_obj):
    rect_tuple = rect_obj.rect()
    if rect_area(rect_tuple) < MIN_RECT_AREA:
        return None

    corners = rect_obj.corners()
    scaled_corners = []
    for point in corners:
        scaled_corners.append(scale_point(point))

    cx = 0
    cy = 0
    for point in scaled_corners:
        cx += point[0]
        cy += point[1]
    cx = cx // 4
    cy = cy // 4

    return {
        "corners": scaled_corners,
        "center_x": cx,
        "center_y": cy,
        "area": rect_area(rect_tuple),
    }


def insert_rect_by_area(rect_list, rect_data):
    rect_list.append(rect_data)
    i = len(rect_list) - 1
    while i > 0 and rect_list[i]["area"] > rect_list[i - 1]["area"]:
        tmp = rect_list[i - 1]
        rect_list[i - 1] = rect_list[i]
        rect_list[i] = tmp
        i -= 1
    if len(rect_list) > MAX_DRAW_RECTS:
        rect_list.pop()


def detect_rects(img):
    img.gamma_corr(GAMMA)
    binary = img.binary([BINARY_THRESHOLD], roi=RECT_ROI)

    packed = []
    for rect_obj in binary.find_rects(roi=RECT_ROI, threshold=RECT_THRESHOLD):
        rect_data = pack_rect(rect_obj)
        if rect_data:
            insert_rect_by_area(packed, rect_data)
    if packed:
        return packed

    for rect_obj in binary.find_rects(roi=RECT_ROI, threshold=FALLBACK_RECT_THRESHOLD):
        rect_data = pack_rect(rect_obj)
        if rect_data:
            insert_rect_by_area(packed, rect_data)
    return packed


def draw_rect_result(img, rect_data):
    corners = rect_data["corners"]
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        img.draw_line(x0, y0, x1, y1, color=(0, 255, 0), thickness=3)
        img.draw_circle(x0, y0, 5, color=(0, 0, 255), thickness=2)

    cx = rect_data["center_x"]
    cy = rect_data["center_y"]
    img.draw_cross(cx, cy, color=(255, 255, 0), size=12, thickness=2)


try:
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
    miss_count = 0
    print("rectangle detect dual-channel start")

    while True:
        os.exitpoint()
        clock.tick()
        display_img = sensor.snapshot(chn=DISPLAY_CHN)

        if frame_id % DETECT_EVERY_N_FRAMES == 0:
            detect_img = sensor.snapshot(chn=DETECT_CHN)
            detected_rects = detect_rects(detect_img)
            if detected_rects:
                last_rects = detected_rects
                miss_count = 0
            else:
                miss_count += 1
                if miss_count >= RECT_MISS_HOLD_FRAMES:
                    last_rects = []

        rect_count = 0
        for rect_data in last_rects:
            draw_rect_result(display_img, rect_data)
            rect_count += 1

        display_img.draw_string_advanced(10, 10, 32,
                                         "RECT:%d FPS:%d" % (rect_count, int(clock.fps())),
                                         color=(255, 0, 0))
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
