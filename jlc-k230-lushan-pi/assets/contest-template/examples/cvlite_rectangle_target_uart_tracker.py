# @runtime: canmv
# @route: rectangle-tracking
# @requires: camera,lcd,cv_lite,uart2

import gc
import os
import time

from machine import FPIOA, UART
from media.sensor import *
from media.display import *
from media.media import *

import cv_lite


DISPLAY_MODE = "lcd"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DETECT_WIDTH = 480
DETECT_HEIGHT = 320
SENSOR_ID = 2

DISPLAY_CHN = CAM_CHN_ID_0
DETECT_CHN = CAM_CHN_ID_1

IMAGE_SHAPE = [DETECT_HEIGHT, DETECT_WIDTH]
LCD_CENTER_X = DISPLAY_WIDTH // 2
LCD_CENTER_Y = DISPLAY_HEIGHT // 2
DETECT_CENTER_X = DETECT_WIDTH // 2
DETECT_CENTER_Y = DETECT_HEIGHT // 2

ENABLE_UART = True
UART_ID = UART.UART2
UART_TX_PIN = 11
UART_RX_PIN = 12
UART_BAUD = 115200
UART_SEND_EVERY_N_FRAMES = 2
SEND_LOST_PACKET = True

STRICT_CANNY1 = 50
STRICT_CANNY2 = 150
STRICT_EPSILON = 0.04
STRICT_AREA_RATIO = 0.001
STRICT_MAX_ANGLE_COS = 0.3
STRICT_BLUR = 5

FALLBACK_CANNY1 = 30
FALLBACK_CANNY2 = 100
FALLBACK_EPSILON = 0.05
FALLBACK_AREA_RATIO = 0.0005
FALLBACK_MAX_ANGLE_COS = 0.5
FALLBACK_BLUR = 5

MIN_DETECT_AREA = 400
LOST_RESET_FRAMES = 8
GC_INTERVAL_FRAMES = 30


sensor = None
uart = None
last_target = None
lost_count = LOST_RESET_FRAMES


def abs_int(value):
    if value < 0:
        return -value
    return value


def scale_x(x):
    return int(x * DISPLAY_WIDTH // DETECT_WIDTH)


def scale_y(y):
    return int(y * DISPLAY_HEIGHT // DETECT_HEIGHT)


def detect_x(x):
    return int(x * DETECT_WIDTH // DISPLAY_WIDTH)


def detect_y(y):
    return int(y * DETECT_HEIGHT // DISPLAY_HEIGHT)


def init_display():
    if DISPLAY_MODE == "lcd":
        Display.init(Display.ST7701, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    elif DISPLAY_MODE == "hdmi":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    else:
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)


def init_uart():
    if not ENABLE_UART:
        return None
    fpioa = FPIOA()
    fpioa.set_function(UART_TX_PIN, FPIOA.UART2_TXD)
    fpioa.set_function(UART_RX_PIN, FPIOA.UART2_RXD)
    return UART(UART_ID, baudrate=UART_BAUD, bits=UART.EIGHTBITS, parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)


def detect_rects_strict(img_np):
    return cv_lite.grayscale_find_rectangles_with_corners(IMAGE_SHAPE, img_np, STRICT_CANNY1, STRICT_CANNY2, STRICT_EPSILON, STRICT_AREA_RATIO, STRICT_MAX_ANGLE_COS, STRICT_BLUR)


def detect_rects_fallback(img_np):
    return cv_lite.grayscale_find_rectangles_with_corners(IMAGE_SHAPE, img_np, FALLBACK_CANNY1, FALLBACK_CANNY2, FALLBACK_EPSILON, FALLBACK_AREA_RATIO, FALLBACK_MAX_ANGLE_COS, FALLBACK_BLUR)


def sort_points(points):
    for i in range(len(points)):
        for j in range(i + 1, len(points)):
            if points[j][0] + points[j][1] < points[i][0] + points[i][1]:
                tmp = points[i]
                points[i] = points[j]
                points[j] = tmp
    top_left = points[0]
    bottom_right = points[3]
    others = [points[1], points[2]]
    if others[0][0] > others[1][0]:
        top_right = others[0]
        bottom_left = others[1]
    else:
        top_right = others[1]
        bottom_left = others[0]
    return [top_left, top_right, bottom_right, bottom_left]


def perspective_center(corners):
    x1 = corners[0][0]
    y1 = corners[0][1]
    x2 = corners[1][0]
    y2 = corners[1][1]
    x3 = corners[2][0]
    y3 = corners[2][1]
    x4 = corners[3][0]
    y4 = corners[3][1]
    denom = (x1 - x3) * (y2 - y4) - (y1 - y3) * (x2 - x4)
    if abs(denom) < 0.0001:
        sx = 0
        sy = 0
        for point in corners:
            sx += point[0]
            sy += point[1]
        return sx // 4, sy // 4
    px = ((x1 * y3 - y1 * x3) * (x2 - x4) - (x1 - x3) * (x2 * y4 - y2 * x4)) / denom
    py = ((x1 * y3 - y1 * x3) * (y2 - y4) - (y1 - y3) * (x2 * y4 - y2 * x4)) / denom
    return int(px), int(py)


def rect_to_target(rect, mode):
    if len(rect) < 12:
        return None
    area = rect[2] * rect[3]
    if area < MIN_DETECT_AREA:
        return None

    corners = []
    i = 4
    while i + 1 < 12:
        corners.append((scale_x(rect[i]), scale_y(rect[i + 1])))
        i += 2
    if len(corners) != 4:
        return None
    corners = sort_points(corners)
    center_x, center_y = perspective_center(corners)
    return {
        "corners": corners,
        "center_x": center_x,
        "center_y": center_y,
        "area": area,
        "mode": mode,
    }


def candidate_score(target):
    if last_target and lost_count < LOST_RESET_FRAMES:
        ref_x = detect_x(last_target["center_x"])
        ref_y = detect_y(last_target["center_y"])
    else:
        ref_x = DETECT_CENTER_X
        ref_y = DETECT_CENTER_Y
    cx = detect_x(target["center_x"])
    cy = detect_y(target["center_y"])
    dx = abs_int(cx - ref_x)
    dy = abs_int(cy - ref_y)
    return target["area"] - (dx * 30) - (dy * 30)


def select_target(rects, mode):
    selected = None
    selected_score = -1000000
    for i in range(len(rects)):
        target = rect_to_target(rects[i], mode)
        if target:
            score = candidate_score(target)
            if score > selected_score:
                selected = target
                selected_score = score
    return selected


def find_target(detect_img):
    img_np = detect_img.to_numpy_ref()
    rects = detect_rects_strict(img_np)
    target = select_target(rects, 1)
    if target:
        return target, len(rects)

    rects = detect_rects_fallback(img_np)
    target = select_target(rects, 2)
    return target, len(rects)


def draw_target(img, target, rect_count, fps):
    img.draw_cross(LCD_CENTER_X, LCD_CENTER_Y, color=(255, 255, 255), size=14, thickness=2)
    if target:
        corners = target["corners"]
        for i in range(4):
            x0 = corners[i][0]
            y0 = corners[i][1]
            x1 = corners[(i + 1) % 4][0]
            y1 = corners[(i + 1) % 4][1]
            img.draw_line(x0, y0, x1, y1, color=(0, 255, 0), thickness=3)
            img.draw_cross(x0, y0, color=(255, 255, 0), size=8, thickness=2)
        cx = target["center_x"]
        cy = target["center_y"]
        img.draw_cross(cx, cy, color=(255, 0, 255), size=22, thickness=3)
        img.draw_circle(cx, cy, 10, color=(255, 0, 255), thickness=2)
        img.draw_string_advanced(8, 8, 28, "CVL:%d M:%d FPS:%d" % (rect_count, target["mode"], int(fps)), color=(255, 0, 0))
        img.draw_string_advanced(8, 40, 24, "C:%d,%d E:%d,%d" % (cx, cy, cx - LCD_CENTER_X, cy - LCD_CENTER_Y), color=(255, 0, 255))
    else:
        img.draw_string_advanced(8, 8, 28, "CVL:0 LOST:%d FPS:%d" % (lost_count, int(fps)), color=(255, 255, 0))


def send_uart_packet(target, frame_id):
    if not uart:
        return
    if frame_id % UART_SEND_EVERY_N_FRAMES != 0:
        return
    if target:
        err_x = target["center_x"] - LCD_CENTER_X
        err_y = target["center_y"] - LCD_CENTER_Y
        uart.write("e,%d,%d\n" % (err_x, err_y))
    elif SEND_LOST_PACKET:
        uart.write("e,999,999\n")


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
    uart = init_uart()

    clock = time.clock()
    frame_id = 0
    rect_count = 0
    print("cv_lite rectangle target uart tracker start")

    while True:
        os.exitpoint()
        clock.tick()
        display_img = sensor.snapshot(chn=DISPLAY_CHN)
        detect_img = sensor.snapshot(chn=DETECT_CHN)
        target, rect_count = find_target(detect_img)
        if target:
            last_target = target
            lost_count = 0
        else:
            lost_count += 1
            if lost_count >= LOST_RESET_FRAMES:
                last_target = None
        draw_target(display_img, last_target, rect_count, clock.fps())
        send_uart_packet(last_target, frame_id)
        Display.show_image(display_img)

        frame_id += 1
        if frame_id % GC_INTERVAL_FRAMES == 0:
            gc.collect()

except KeyboardInterrupt:
    print("user stopped")
except Exception as e:
    print("error:", e)
finally:
    if uart:
        uart.deinit()
    if isinstance(sensor, Sensor):
        sensor.stop()
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    MediaManager.deinit()
    gc.collect()
