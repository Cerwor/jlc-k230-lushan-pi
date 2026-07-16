# @runtime: canmv
# @route: data-capture
# @requires: camera,lcd,gpio,sdcard

import os
import time

from machine import FPIOA, Pin
from media.sensor import *
from media.display import *
from media.media import *


BUTTON_PAD = 52
BUTTON_GPIO_FUNC = FPIOA.GPIO53
BUTTON_PIN_ID = 53
DEBOUNCE_MS = 300
SAVE_INTERVAL_MS = 1000
# 默认保存到 TF 卡，便于离线采集后直接取卡拷贝样本。
SAVE_DIR = "/sdcard/capture"

fpioa = FPIOA()
fpioa.set_function(BUTTON_PAD, BUTTON_GPIO_FUNC)
button = Pin(BUTTON_PIN_ID, Pin.IN, Pin.PULL_DOWN)

try:
    os.mkdir(SAVE_DIR)
except OSError:
    pass

sensor = None
capture_on = False
last_btn = 0
last_press_time = 0
last_save_time = 0
img_count = 0

try:
    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(sensor.WVGA)
    sensor.set_pixformat(Sensor.RGB565)

    Display.init(Display.ST7701, width=800, height=480, to_ide=True)
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    while True:
        os.exitpoint()
        clock.tick()
        now = time.ticks_ms()

        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        btn = button.value()
        if btn == 1 and last_btn == 0 and time.ticks_diff(now, last_press_time) > DEBOUNCE_MS:
            capture_on = not capture_on
            last_press_time = now
            if capture_on:
                capture_state = "on"
            else:
                capture_state = "off"
            print("capture", capture_state)
        last_btn = btn

        if capture_on and time.ticks_diff(now, last_save_time) >= SAVE_INTERVAL_MS:
            last_save_time = now
            img_count += 1
            filename = "%s/img_%04d.jpg" % (SAVE_DIR, img_count)
            img.save(filename)
            print("saved:", filename)

        img.draw_string_advanced(20, 20, 48,
                                 "FPS:%d" % int(clock.fps()),
                                 color=(255, 0, 0))
        if capture_on:
            capture_label = "ON"
        else:
            capture_label = "OFF"
        img.draw_string_advanced(20, 80, 40,
                                 "CAP:%s" % capture_label,
                                 color=(255, 255, 0))
        img.draw_string_advanced(20, 140, 40,
                                 "SAVED:%d" % img_count,
                                 color=(0, 255, 0))
        Display.show_image(img)

except KeyboardInterrupt:
    print("stopped")
except Exception as e:
    print("error:", e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
