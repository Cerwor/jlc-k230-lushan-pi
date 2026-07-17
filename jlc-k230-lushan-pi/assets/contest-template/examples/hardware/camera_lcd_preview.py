# @runtime: canmv
# @route: bring-up
# @requires: camera,lcd

import os
import time

from media.sensor import *
from media.display import *
from media.media import *


sensor = None

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
        img = sensor.snapshot(chn=CAM_CHN_ID_0)
        img.draw_string_advanced(20, 20, 48,
                                 "FPS:%d" % int(clock.fps()),
                                 color=(255, 0, 0))
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
