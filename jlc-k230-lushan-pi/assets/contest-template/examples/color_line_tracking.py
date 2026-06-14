import gc
import os
import time

from media.sensor import *
from media.display import *
from media.media import *


DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
SENSOR_ID = 2

COLOR_THRESHOLDS = [(41, 57, 31, 83, 13, 71)]
BLOB_ROI = (0, 0, 640, 360)
LINE_ROI_HALF = (0, 0, 320, 180)
BLOB_PIXELS_THRESHOLD = 800
LINE_MIN_LENGTH = 60
GC_INTERVAL_FRAMES = 30


sensor = None


try:
    sensor = Sensor(id=SENSOR_ID)
    sensor.reset()
    sensor.set_framesize(width=640, height=360)
    sensor.set_pixformat(Sensor.RGB565)

    Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    MediaManager.init()
    sensor.run()

    clock = time.clock()
    frame_id = 0

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=CAM_CHN_ID_0)

        blob_count = 0
        blobs = img.find_blobs(COLOR_THRESHOLDS, False, BLOB_ROI,
                               x_stride=5, y_stride=5,
                               pixels_threshold=BLOB_PIXELS_THRESHOLD,
                               margin=True)
        for blob in blobs:
            blob_count += 1
            img.draw_rectangle(blob.x(), blob.y(), blob.w(), blob.h(),
                               color=(0, 255, 0), thickness=3)
            img.draw_cross(blob.cx(), blob.cy(), color=(255, 255, 0), size=8, thickness=2)

        line_img = img.to_rgb565(copy=True)
        line_img.midpoint_pool(2, 2)
        lines = line_img.find_line_segments(LINE_ROI_HALF, 15, 15)
        line_count = 0
        for line in lines:
            if line.length() > LINE_MIN_LENGTH:
                line_count += 1
                img.draw_line(line.x1() * 2, line.y1() * 2,
                              line.x2() * 2, line.y2() * 2,
                              color=(255, 0, 0), thickness=3)

        img.draw_string_advanced(10, 10, 28,
                                 "B:%d L:%d FPS:%d" % (blob_count, line_count, int(clock.fps())),
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
