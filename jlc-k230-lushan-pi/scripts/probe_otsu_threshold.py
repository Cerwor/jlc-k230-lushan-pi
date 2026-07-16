# @runtime: canmv
# @route: threshold-acceptance
# @requires: camera,lcd

import gc
import os
import time

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

GRAY_THRESHOLD = [0, 100]
GRAY_DEFAULT_THRESHOLD = (0, 100)
BLOB_ROI = (0, 0, DETECT_WIDTH, DETECT_HEIGHT)
BLOB_PIXELS_THRESHOLD = 300
OTSU_SAMPLE_FRAMES = 30
OTSU_VERIFY_FRAMES = 5
OTSU_VALID_MIN = 50
OTSU_VALID_MAX = 180
OTSU_MARGIN = 15
RESULT_FRAMES = 20


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def get_threshold_value(threshold_obj):
    if hasattr(threshold_obj, "value"):
        return int(threshold_obj.value())
    return int(threshold_obj)


def find_gray_blobs(img):
    gray = img.to_grayscale(copy=True)
    return gray.find_blobs([tuple(GRAY_THRESHOLD)], False, BLOB_ROI,
                           x_stride=5, y_stride=5,
                           pixels_threshold=BLOB_PIXELS_THRESHOLD,
                           margin=True)


def verify_gray_threshold(sensor_obj):
    for i in range(OTSU_VERIFY_FRAMES):
        os.exitpoint()
        img = sensor_obj.snapshot(chn=DETECT_CHN)
        try:
            blobs = find_gray_blobs(img)
            if blobs:
                print("OTSU_VERIFY_HIT frame=%d blobs=%d" % (i, len(blobs)))
                return True
        except Exception as e:
            print("OTSU_VERIFY_WARN frame=%d err=%s" % (i, e))
        time.sleep_ms(30)
    return False


def auto_calibrate_gray_otsu(sensor_obj):
    samples = []
    print("OTSU_PROBE_START frames=%d" % OTSU_SAMPLE_FRAMES)
    for i in range(OTSU_SAMPLE_FRAMES):
        os.exitpoint()
        img = sensor_obj.snapshot(chn=DETECT_CHN)
        try:
            gray = img.to_grayscale(copy=True)
            hist = gray.get_histogram()
            value = get_threshold_value(hist.get_threshold())
            print("OTSU_SAMPLE frame=%d threshold=%d" % (i, value))
            if OTSU_VALID_MIN < value and value < OTSU_VALID_MAX:
                samples.append(value)
        except Exception as e:
            print("OTSU_SAMPLE_WARN frame=%d err=%s" % (i, e))
        time.sleep_ms(20)

    if len(samples) >= 5:
        total = 0
        for value in samples:
            total += value
        avg = total // len(samples)
        if OTSU_VALID_MIN < avg and avg < OTSU_VALID_MAX:
            GRAY_THRESHOLD[0] = 0
            GRAY_THRESHOLD[1] = clamp(avg + OTSU_MARGIN, 0, 255)

    verified = verify_gray_threshold(sensor_obj)
    if not verified:
        GRAY_THRESHOLD[0] = GRAY_DEFAULT_THRESHOLD[0]
        GRAY_THRESHOLD[1] = GRAY_DEFAULT_THRESHOLD[1]
        print("OTSU_PROBE_FALLBACK threshold=%d..%d samples=%d" %
              (GRAY_THRESHOLD[0], GRAY_THRESHOLD[1], len(samples)))
    else:
        print("OTSU_PROBE_OK threshold=%d..%d samples=%d" %
              (GRAY_THRESHOLD[0], GRAY_THRESHOLD[1], len(samples)))
    return verified, len(samples)


sensor = None

try:
    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, chn=DISPLAY_CHN)
    sensor.set_pixformat(Sensor.RGB565, chn=DISPLAY_CHN)
    sensor.set_framesize(width=DETECT_WIDTH, height=DETECT_HEIGHT, chn=DETECT_CHN)
    sensor.set_pixformat(Sensor.RGB565, chn=DETECT_CHN)
    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()
    verified, sample_count = auto_calibrate_gray_otsu(sensor)

    for i in range(RESULT_FRAMES):
        os.exitpoint()
        img = sensor.snapshot(chn=DISPLAY_CHN)
        img.draw_string_advanced(10, 10, 32,
                                 "OTSU verified=%d samples=%d" % (int(verified), sample_count),
                                 color=(255, 0, 0))
        img.draw_string_advanced(10, 50, 28,
                                 "GRAY %d..%d" % (GRAY_THRESHOLD[0], GRAY_THRESHOLD[1]),
                                 color=(255, 255, 0))
        Display.show_image(img)
    print("OTSU_PROBE_DONE verified=%d threshold=%d..%d samples=%d" %
          (int(verified), GRAY_THRESHOLD[0], GRAY_THRESHOLD[1], sample_count))

except Exception as e:
    print("OTSU_PROBE_ERROR:", e)
finally:
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    gc.collect()
