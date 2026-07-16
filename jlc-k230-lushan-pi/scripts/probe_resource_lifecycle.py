# @runtime: canmv
# @route: resource-lifecycle
# @requires: camera,lcd

import gc
import os
import time

from media.sensor import *
from media.display import *
from media.media import *


CYCLE_LIMIT = 3
FRAMES_PER_CYCLE = 3
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
SENSOR_ID = 2


def free_heap():
    try:
        return gc.mem_free()
    except Exception:
        return -1


def cleanup_cycle(sensor):
    if sensor is not None:
        try:
            sensor.stop()
        except Exception as e:
            print("LIFECYCLE_SENSOR_STOP_WARN", e)

    try:
        Display.deinit()
    except Exception as e:
        print("LIFECYCLE_DISPLAY_DEINIT_WARN", e)

    try:
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        MediaManager.deinit()
    except Exception as e:
        print("LIFECYCLE_MEDIA_DEINIT_WARN", e)

    gc.collect()
    time.sleep_ms(100)


def run_cycle(index):
    sensor = None
    ok = 0
    try:
        sensor = Sensor(id=SENSOR_ID)
        sensor.reset()
        sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=CAM_CHN_ID_0)
        sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)

        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
        MediaManager.init()
        sensor.run()

        frame_id = 0
        while frame_id < FRAMES_PER_CYCLE:
            os.exitpoint()
            img = sensor.snapshot(chn=CAM_CHN_ID_0)
            img.draw_string_advanced(10, 10, 28,
                                     "LIFECYCLE %d/%d" % (index, frame_id),
                                     color=(255, 255, 0))
            Display.show_image(img)
            frame_id += 1
        ok = 1
    except Exception as e:
        print("LIFECYCLE_CYCLE_ERROR index=%d err=%s" % (index, e))
    finally:
        cleanup_cycle(sensor)

    print("LIFECYCLE_CYCLE index=%d ok=%d mem=%d" % (index, ok, free_heap()))
    return ok


def main():
    gc.collect()
    mem_start = free_heap()
    min_mem = mem_start
    passed = 0
    index = 1
    while index <= CYCLE_LIMIT:
        passed += run_cycle(index)
        current_mem = free_heap()
        if min_mem < 0 or (current_mem >= 0 and current_mem < min_mem):
            min_mem = current_mem
        index += 1

    mem_end = free_heap()
    print("LIFECYCLE_PROBE_DONE cycles=%d passed=%d mem_start=%d mem_end=%d min_mem=%d" %
          (CYCLE_LIMIT, passed, mem_start, mem_end, min_mem))


try:
    main()
except Exception as e:
    print("LIFECYCLE_PROBE_FATAL", e)
    print("LIFECYCLE_PROBE_DONE cycles=%d passed=0 mem_start=-1 mem_end=-1 min_mem=-1" % CYCLE_LIMIT)
finally:
    gc.collect()
