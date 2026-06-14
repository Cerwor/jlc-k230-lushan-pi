import os
import time

from machine import FPIOA, Pin
from media.sensor import *
from media.display import *
from media.media import *


SENSOR_ID = 2
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480

KEY_NEXT_PIN = 53
KEY_INC_PIN = 32
KEY_DEC_PIN = 34

threshold = [41, 57, 31, 83, 13, 71]
selected = 0
names = ["Lmin", "Lmax", "Amin", "Amax", "Bmin", "Bmax"]


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def update_key(key, last, callback):
    now = time.ticks_ms()
    value = key.value()
    if value == 1 and last[0] == 0 and time.ticks_diff(now, last[1]) > 250:
        callback()
        last[1] = now
    last[0] = value


sensor = None

try:
    fpioa = FPIOA()
    fpioa.set_function(KEY_NEXT_PIN, getattr(FPIOA, "GPIO%d" % KEY_NEXT_PIN))
    fpioa.set_function(KEY_INC_PIN, getattr(FPIOA, "GPIO%d" % KEY_INC_PIN))
    fpioa.set_function(KEY_DEC_PIN, getattr(FPIOA, "GPIO%d" % KEY_DEC_PIN))
    key_next = Pin(KEY_NEXT_PIN, Pin.IN, Pin.PULL_DOWN)
    key_inc = Pin(KEY_INC_PIN, Pin.IN, Pin.PULL_UP)
    key_dec = Pin(KEY_DEC_PIN, Pin.IN, Pin.PULL_UP)
    last_next = [0, 0]
    last_inc = [1, 0]
    last_dec = [1, 0]

    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=640, height=360)
    sensor.set_pixformat(Sensor.RGB565)
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

    while True:
        os.exitpoint()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        blobs = img.find_blobs([tuple(threshold)], False, (0, 0, 640, 360),
                               x_stride=5, y_stride=5, pixels_threshold=500, margin=True)
        for blob in blobs:
            img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(), color=(0, 255, 0), thickness=3)
            img.draw_cross(blob.cx(), blob.cy(), color=(255, 255, 0), size=8, thickness=2)

        update_key(key_next, last_next, next_param)
        update_key(key_inc, last_inc, inc_param)
        update_key(key_dec, last_dec, dec_param)

        img.draw_string_advanced(10, 10, 28, "%s=%d" % (names[selected], threshold[selected]), color=(255, 0, 0))
        img.draw_string_advanced(10, 45, 24, str(threshold), color=(255, 255, 0))
        Display.show_image(img)

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
