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

CIRCLE_ROI = (80, 40, 240, 160)  # Detection-image coordinates, not LCD coordinates.
X_STRIDE = 4
Y_STRIDE = 4
CIRCLE_THRESHOLD = 2500
X_MARGIN = 10
Y_MARGIN = 10
R_MARGIN = 10
MIN_RADIUS = 6
MAX_RADIUS = 80

DETECT_EVERY_N_FRAMES = 3
ENABLE_SERIAL_PRINT = False
PRINT_EVERY_N_FRAMES = 15
GC_INTERVAL_FRAMES = 30


sensor = None
last_circles = []


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


def detect_circles(img):
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
        found.append({
            "detect_x": circle.x(),
            "detect_y": circle.y(),
            "detect_r": radius,
            "lcd_x": int(circle.x() * SCALE_X),
            "lcd_y": int(circle.y() * SCALE_Y),
            "lcd_r": int(radius * (SCALE_X + SCALE_Y) / 2),
            "score": circle_score(circle),
        })
    for i in range(len(found)):
        for j in range(i + 1, len(found)):
            if found[j]["score"] > found[i]["score"]:
                found[i], found[j] = found[j], found[i]
    return found


def draw_overlay(img, circles, fps):
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
        text = "C:%d,%d R:%d FPS:%d" % (
            first["lcd_x"], first["lcd_y"], first["lcd_r"], int(fps))
    else:
        text = "NO CIRCLE FPS:%d" % int(fps)
    img.draw_string_advanced(10, 10, 28, text, color=(255, 0, 0))


def maybe_print(frame_id, circles, fps):
    if not ENABLE_SERIAL_PRINT or frame_id % PRINT_EVERY_N_FRAMES != 0:
        return
    if circles:
        first = circles[0]
        print("circle lcd=(%d,%d,%d) detect=(%d,%d,%d) fps=%d" % (
            first["lcd_x"], first["lcd_y"], first["lcd_r"],
            first["detect_x"], first["detect_y"], first["detect_r"],
            int(fps)))
    else:
        print("no circle fps=%d" % int(fps))


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
    print("circle detect dual-channel start")

    while True:
        os.exitpoint()
        clock.tick()
        display_img = sensor.snapshot(chn=DISPLAY_CHN)

        if frame_id % DETECT_EVERY_N_FRAMES == 0:
            detect_img = sensor.snapshot(chn=DETECT_CHN)
            last_circles = detect_circles(detect_img)

        draw_overlay(display_img, last_circles, clock.fps())
        maybe_print(frame_id, last_circles, clock.fps())
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
