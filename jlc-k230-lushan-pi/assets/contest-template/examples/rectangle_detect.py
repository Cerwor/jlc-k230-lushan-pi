import gc
import os
import time

from media.sensor import *
from media.display import *
from media.media import *


DISPLAY_MODE = "lcd"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
SENSOR_ID = 2
FRAME_SIZE = Sensor.WVGA
PIXFORMAT = Sensor.RGB565

RECT_THRESHOLD = 8000
MIN_RECT_AREA = 400
GC_INTERVAL_FRAMES = 30


sensor = None


def init_display():
    if DISPLAY_MODE == "lcd":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "hdmi":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    else:
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)


def rect_area(rect_tuple):
    return rect_tuple[2] * rect_tuple[3]


def draw_rect_result(img, rect_obj):
    rect_tuple = rect_obj.rect()
    if rect_area(rect_tuple) < MIN_RECT_AREA:
        return False

    img.draw_rectangle(rect_tuple, color=(255, 0, 0), thickness=3)
    corners = rect_obj.corners()
    for i in range(4):
        x0, y0 = corners[i]
        x1, y1 = corners[(i + 1) % 4]
        img.draw_line(x0, y0, x1, y1, color=(0, 255, 0), thickness=3)
        img.draw_circle(x0, y0, 5, color=(0, 0, 255), thickness=2)

    cx = rect_tuple[0] + rect_tuple[2] // 2
    cy = rect_tuple[1] + rect_tuple[3] // 2
    img.draw_cross(cx, cy, color=(255, 255, 0), size=10, thickness=2)
    return True


try:
    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(FRAME_SIZE, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(PIXFORMAT, chn=CAM_CHN_ID_0)

    init_display()
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    frame_id = 0
    print("rectangle detect test start")

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        rect_count = 0
        for rect_obj in img.find_rects(threshold=RECT_THRESHOLD):
            if draw_rect_result(img, rect_obj):
                rect_count += 1

        img.draw_string_advanced(10, 10, 32,
                                 "RECT:%d FPS:%d" % (rect_count, int(clock.fps())),
                                 color=(255, 0, 0))
        Display.show_image(img)

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
