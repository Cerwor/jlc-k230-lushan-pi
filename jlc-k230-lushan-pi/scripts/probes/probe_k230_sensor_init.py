# @runtime: canmv
# @route: sensor-diagnosis
# @requires: camera

import gc
import os
import time

from media.sensor import *
from media.media import *


TESTS = (
    ("ID2_LCD_800x480", 2, 0, 0, 800, 480, 1),
    ("ID2_QVGA_320x240", 2, 0, 0, 320, 240, 1),
    ("DEFAULT_QVGA", -1, 0, 0, 320, 240, 1),
    ("ID0_QVGA", 0, 0, 0, 320, 240, 1),
    ("ID1_QVGA", 1, 0, 0, 320, 240, 1),
    ("ID0_FHD_CTOR_QVGA", 0, 1920, 1080, 320, 240, 1),
)

ATTRS = (
    "CAM_CHN_ID_0",
    "CAM_CHN_ID_1",
    "CAM_CHN_ID_2",
    "RGB565",
    "RGB888",
    "YUV420SP",
    "GRAYSCALE",
    "QVGA",
    "VGA",
    "HD",
    "FHD",
)


def make_sensor(sensor_id, ctor_width, ctor_height):
    if ctor_width > 0 and ctor_height > 0:
        return Sensor(id=sensor_id, width=ctor_width, height=ctor_height)
    if sensor_id >= 0:
        return Sensor(id=sensor_id)
    return Sensor()


def stop_sensor(sensor):
    if sensor is None:
        return
    try:
        sensor.stop()
    except Exception as e:
        print("SENSOR_STOP_WARN:", e)


def deinit_media():
    try:
        MediaManager.deinit()
    except Exception as e:
        print("MEDIA_DEINIT_WARN:", e)


def try_snapshot(sensor, use_channel):
    if use_channel:
        return sensor.snapshot(chn=CAM_CHN_ID_0)
    return sensor.snapshot()


def try_mode(name, sensor_id, ctor_width, ctor_height, frame_width, frame_height, use_channel):
    sensor = None
    media_started = False
    print("SENSOR_PROBE_BEGIN %s" % name)
    try:
        sensor = make_sensor(sensor_id, ctor_width, ctor_height)
        sensor.reset()
        if use_channel:
            sensor.set_framesize(width=frame_width, height=frame_height, chn=CAM_CHN_ID_0)
            sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_0)
        else:
            sensor.set_framesize(width=frame_width, height=frame_height)
            sensor.set_pixformat(Sensor.RGB565)
        MediaManager.init()
        media_started = True
        sensor.run()
        time.sleep_ms(100)
        os.exitpoint()
        img = try_snapshot(sensor, use_channel)
        print("SENSOR_PROBE_OK %s size=%dx%d" % (name, img.width(), img.height()))
        return True
    except Exception as e:
        print("SENSOR_PROBE_FAIL %s err=%s" % (name, e))
        return False
    finally:
        stop_sensor(sensor)
        if media_started:
            deinit_media()
        time.sleep_ms(100)
        gc.collect()


def print_sensor_attrs():
    print("SENSOR_ATTRS_BEGIN")
    for name in ATTRS:
        if name in globals():
            print("SENSOR_GLOBAL %s=%s" % (name, globals()[name]))
        else:
            try:
                value = getattr(Sensor, name)
                print("SENSOR_ATTR %s=%s" % (name, value))
            except Exception as e:
                print("SENSOR_ATTR_FAIL %s err=%s" % (name, e))
    print("SENSOR_ATTRS_END")


def main():
    ok_count = 0
    print("SENSOR_PROBE_START")
    for item in TESTS:
        ok = try_mode(item[0], item[1], item[2], item[3], item[4], item[5], item[6])
        if ok:
            ok_count += 1
    print_sensor_attrs()
    print("SENSOR_PROBE_DONE ok=%d total=%d" % (ok_count, len(TESTS)))


try:
    main()
except Exception as e:
    print("SENSOR_PROBE_FATAL:", e)
finally:
    deinit_media()
    gc.collect()
