import gc
import os
import time

from machine import FPIOA, Pin
from media.sensor import *
from media.display import *
from media.media import *


SENSOR_ID = 2
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DETECT_WIDTH = 400
DETECT_HEIGHT = 240

DISPLAY_CHN = CAM_CHN_ID_0
DETECT_CHN = CAM_CHN_ID_1

SCALE_X = DISPLAY_WIDTH // DETECT_WIDTH
SCALE_Y = DISPLAY_HEIGHT // DETECT_HEIGHT

KEY_NEXT_PIN = 53
KEY_INC_PIN = 32
KEY_DEC_PIN = 34
KEY_NEXT_ACTIVE = 0
KEY_INC_ACTIVE = 0
KEY_DEC_ACTIVE = 0

threshold = [41, 57, 31, 83, 13, 71]
selected = 0
names = ["Lmin", "Lmax", "Amin", "Amax", "Bmin", "Bmax"]
BLOB_ROI = (0, 0, DETECT_WIDTH, DETECT_HEIGHT)
BLOB_PIXELS_THRESHOLD = 300
GC_INTERVAL_FRAMES = 30


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def update_key(key, last, active_value, callback):
    now = time.ticks_ms()
    value = key.value()
    if value == active_value and last[0] != active_value and time.ticks_diff(now, last[1]) > 250:
        callback()
        last[1] = now
    last[0] = value


def scale_x(x):
    return int(x * SCALE_X)


def scale_y(y):
    return int(y * SCALE_Y)


def pack_blobs(img):
    packed = []
    blobs = img.find_blobs([tuple(threshold)], False, BLOB_ROI,
                           x_stride=5, y_stride=5,
                           pixels_threshold=BLOB_PIXELS_THRESHOLD,
                           margin=True)
    for blob in blobs:
        packed.append((scale_x(blob.x()), scale_y(blob.y()),
                       scale_x(blob.w()), scale_y(blob.h()),
                       scale_x(blob.cx()), scale_y(blob.cy()),
                       blob.pixels()))
    return packed


def draw_ui(img, blobs, fps):
    for blob in blobs:
        img.draw_rectangle(blob[0], blob[1], blob[2], blob[3], color=(0, 255, 0), thickness=3)
        img.draw_cross(blob[4], blob[5], color=(255, 255, 0), size=10, thickness=2)

    line1 = "%s=%d FPS:%d" % (names[selected], threshold[selected], int(fps))
    line2 = str(threshold)
    line3 = "B:%d  NEXT:%d INC:%d DEC:%d" % (len(blobs), KEY_NEXT_PIN, KEY_INC_PIN, KEY_DEC_PIN)
    img.draw_string_advanced(10, 10, 28, line1, color=(255, 0, 0))
    img.draw_string_advanced(10, 45, 24, line2, color=(255, 255, 0))
    img.draw_string_advanced(10, 80, 24, line3, color=(0, 255, 0))


sensor = None

try:
    fpioa = FPIOA()
    fpioa.set_function(KEY_NEXT_PIN, getattr(FPIOA, "GPIO%d" % KEY_NEXT_PIN))
    fpioa.set_function(KEY_INC_PIN, getattr(FPIOA, "GPIO%d" % KEY_INC_PIN))
    fpioa.set_function(KEY_DEC_PIN, getattr(FPIOA, "GPIO%d" % KEY_DEC_PIN))
    key_next = Pin(KEY_NEXT_PIN, Pin.IN, Pin.PULL_UP)
    key_inc = Pin(KEY_INC_PIN, Pin.IN, Pin.PULL_UP)
    key_dec = Pin(KEY_DEC_PIN, Pin.IN, Pin.PULL_UP)
    now_ms = time.ticks_ms()
    last_next = [key_next.value(), now_ms]
    last_inc = [key_inc.value(), now_ms]
    last_dec = [key_dec.value(), now_ms]

    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=DISPLAY_CHN)
    sensor.set_pixformat(Sensor.RGB565, chn=DISPLAY_CHN)
    sensor.set_framesize(width=DETECT_WIDTH, height=DETECT_HEIGHT, chn=DETECT_CHN)
    sensor.set_pixformat(Sensor.RGB565, chn=DETECT_CHN)
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    def next_param():
        global selected
        selected = (selected + 1) % 6

    def inc_param():
        threshold[selected] = clamp(threshold[selected] + 1, -128, 255)

    def dec_param():
        threshold[selected] = clamp(threshold[selected] - 1, -128, 255)

    clock = time.clock()
    frame_id = 0
    while True:
        os.exitpoint()
        clock.tick()
        display_img = sensor.snapshot(chn=DISPLAY_CHN)
        detect_img = sensor.snapshot(chn=DETECT_CHN)
        blobs = pack_blobs(detect_img)

        update_key(key_next, last_next, KEY_NEXT_ACTIVE, next_param)
        update_key(key_inc, last_inc, KEY_INC_ACTIVE, inc_param)
        update_key(key_dec, last_dec, KEY_DEC_ACTIVE, dec_param)

        draw_ui(display_img, blobs, clock.fps())
        Display.show_image(display_img)
        frame_id += 1
        if frame_id % GC_INTERVAL_FRAMES == 0:
            gc.collect()

except KeyboardInterrupt:
    print("user stopped")
except Exception as e:
    print("error:", e)
finally:
    if sensor is not None:
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    gc.collect()
