# @runtime: canmv
# @route: bring-up
# @requires: camera,lcd

import gc
import os
import time

from media.sensor import *
from media.display import *
from media.media import *


FRAME_LIMIT = 20
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
SENSOR_ID = 2

sensor = None

try:
    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=CAM_CHN_ID_0)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    frame_id = 0
    print("SMOKE_START")
    while frame_id < FRAME_LIMIT:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        img.draw_string_advanced(10, 10, 32,
                                 "SMOKE %d FPS:%d" % (frame_id, int(clock.fps())),
                                 color=(255, 0, 0))
        Display.show_image(img)
        frame_id += 1
    print("SMOKE_DONE frames=%d fps=%d" % (frame_id, int(clock.fps())))

except Exception as e:
    print("SMOKE_ERROR:", e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    gc.collect()
