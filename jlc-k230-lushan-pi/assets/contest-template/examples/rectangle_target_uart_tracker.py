import gc
import os
import time

from machine import FPIOA, UART
from media.sensor import *
from media.display import *
from media.media import *


DISPLAY_MODE = "lcd"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
DETECT_WIDTH = 400
DETECT_HEIGHT = 240
SENSOR_ID = 2

DISPLAY_CHN = CAM_CHN_ID_0
DETECT_CHN = CAM_CHN_ID_1

ENABLE_UART = True
UART_ID = UART.UART2
UART_TX_PIN = 11
UART_RX_PIN = 12
UART_BAUD = 115200

ROI_MARGIN = 20
ROI_X = ROI_MARGIN
ROI_Y = ROI_MARGIN
ROI_W = DISPLAY_WIDTH - 2 * ROI_MARGIN
ROI_H = DISPLAY_HEIGHT - 2 * ROI_MARGIN
DETECT_ROI_X = ROI_X * DETECT_WIDTH // DISPLAY_WIDTH
DETECT_ROI_Y = ROI_Y * DETECT_HEIGHT // DISPLAY_HEIGHT
DETECT_ROI_W = ROI_W * DETECT_WIDTH // DISPLAY_WIDTH
DETECT_ROI_H = ROI_H * DETECT_HEIGHT // DISPLAY_HEIGHT
DETECT_ROI = (DETECT_ROI_X, DETECT_ROI_Y, DETECT_ROI_W, DETECT_ROI_H)

GAMMA = 3
BINARY_THRESHOLD = (160, 255)
RECT_THRESHOLD = 2500
FALLBACK_RECT_THRESHOLD = 5000
MIN_AREA = 7000
MIN_ASPECT = 0.5
MAX_ASPECT = 2.5
DETECT_EVERY_N_FRAMES = 2
GC_INTERVAL_FRAMES = 30


sensor = None
uart = None


class TargetTracker:
    def __init__(self):
        self.last_target = None

    def update(self, candidates):
        if not candidates:
            self.last_target = None
            return None
        if self.last_target is None:
            selected = candidates[0]
            for item in candidates:
                if item["area"] > selected["area"]:
                    selected = item
        else:
            lx = self.last_target["center_x"]
            ly = self.last_target["center_y"]
            selected = candidates[0]
            best_dist = None
            for item in candidates:
                dx = item["center_x"] - lx
                dy = item["center_y"] - ly
                dist = dx * dx + dy * dy
                if best_dist is None or dist < best_dist:
                    best_dist = dist
                    selected = item
        self.last_target = selected
        return selected


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
    return UART(UART_ID, baudrate=UART_BAUD, bits=UART.EIGHTBITS,
                parity=UART.PARITY_NONE, stop=UART.STOPBITS_ONE)


def scale_x(x):
    return int(x * DISPLAY_WIDTH // DETECT_WIDTH)


def scale_y(y):
    return int(y * DISPLAY_HEIGHT // DETECT_HEIGHT)


def scale_point(point):
    return scale_x(point[0]), scale_y(point[1])


def sort_corners(corners):
    corners = list(corners)
    for i in range(len(corners)):
        for j in range(i + 1, len(corners)):
            if corners[j][0] + corners[j][1] < corners[i][0] + corners[i][1]:
                corners[i], corners[j] = corners[j], corners[i]
    top_left = corners[0]
    bottom_right = corners[-1]
    others = []
    for point in corners:
        if point != top_left and point != bottom_right:
            others.append(point)
    if len(others) != 2:
        return corners
    if others[0][0] > others[1][0]:
        top_right = others[0]
        bottom_left = others[1]
    else:
        top_right = others[1]
        bottom_left = others[0]
    return [top_left, top_right, bottom_right, bottom_left]


def perspective_center(corners):
    if len(corners) != 4:
        return None, None
    x1, y1 = corners[0]
    x3, y3 = corners[2]
    x2, y2 = corners[1]
    x4, y4 = corners[3]
    denom = (x1 - x3) * (y2 - y4) - (y1 - y3) * (x2 - x4)
    if abs(denom) < 1e-6:
        sum_x = 0
        sum_y = 0
        for point in corners:
            sum_x += point[0]
            sum_y += point[1]
        return sum_x // 4, sum_y // 4
    px = ((x1 * y3 - y1 * x3) * (x2 - x4) - (x1 - x3) * (x2 * y4 - y2 * x4)) / denom
    py = ((x1 * y3 - y1 * x3) * (y2 - y4) - (y1 - y3) * (x2 * y4 - y2 * x4)) / denom
    return int(px), int(py)


def in_roi(corners):
    for x, y in corners:
        if not (ROI_X <= x < ROI_X + ROI_W and ROI_Y <= y < ROI_Y + ROI_H):
            return False
    return True


def rect_to_candidate(rect_obj):
    corners = rect_obj.corners()
    if len(corners) != 4:
        return None
    int_corners = []
    for point in corners:
        int_corners.append(scale_point(point))
    corners = sort_corners(int_corners)
    if not in_roi(corners):
        return None

    x_min = corners[0][0]
    y_min = corners[0][1]
    x_max = corners[0][0]
    y_max = corners[0][1]
    for point in corners:
        if point[0] < x_min:
            x_min = point[0]
        if point[1] < y_min:
            y_min = point[1]
        if point[0] > x_max:
            x_max = point[0]
        if point[1] > y_max:
            y_max = point[1]
    width = x_max - x_min
    height = y_max - y_min
    if width <= 0 or height <= 0:
        return None

    if width > height:
        aspect = width / height
    else:
        aspect = height / width
    area = width * height
    if area < MIN_AREA or aspect < MIN_ASPECT or aspect > MAX_ASPECT:
        return None

    center_x, center_y = perspective_center(corners)
    if center_x is None:
        return None
    return {
        "corners": corners,
        "center_x": center_x,
        "center_y": center_y,
        "area": area,
        "rect": (x_min, y_min, width, height),
    }


def find_candidates(img):
    img.gamma_corr(GAMMA)
    binary = img.binary([BINARY_THRESHOLD], roi=DETECT_ROI)

    candidates = []
    for rect_obj in binary.find_rects(roi=DETECT_ROI, threshold=RECT_THRESHOLD):
        candidate = rect_to_candidate(rect_obj)
        if candidate:
            candidates.append(candidate)

    if candidates:
        return candidates

    for rect_obj in binary.find_rects(roi=DETECT_ROI, threshold=FALLBACK_RECT_THRESHOLD):
        candidate = rect_to_candidate(rect_obj)
        if candidate:
            candidates.append(candidate)
    return candidates


def draw_target(img, target, fps):
    img.draw_rectangle((ROI_X, ROI_Y, ROI_W, ROI_H), color=(40, 40, 255), thickness=2)
    if target:
        corners = target["corners"]
        for i in range(4):
            x0, y0 = corners[i]
            x1, y1 = corners[(i + 1) % 4]
            img.draw_line(x0, y0, x1, y1, color=(0, 255, 0), thickness=3)
            img.draw_circle(x0, y0, 5, color=(255, 255, 0), thickness=2)
        cx = target["center_x"]
        cy = target["center_y"]
        img.draw_cross(cx, cy, size=12, color=(255, 0, 0), thickness=2)
        img.draw_string_advanced(10, 10, 28, "T:%d,%d FPS:%d" % (cx, cy, int(fps)),
                                 color=(255, 0, 0))
    else:
        img.draw_string_advanced(10, 10, 28, "NO TARGET FPS:%d" % int(fps),
                                 color=(255, 0, 0))


def send_target(target):
    if not uart or not target:
        return
    uart.write("t,%d,%d\n" % (target["center_x"], target["center_y"]))


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

    tracker = TargetTracker()
    clock = time.clock()
    frame_id = 0
    print("rectangle target uart tracker start")

    while True:
        os.exitpoint()
        clock.tick()
        img = sensor.snapshot(chn=DISPLAY_CHN)
        if frame_id % DETECT_EVERY_N_FRAMES == 0:
            detect_img = sensor.snapshot(chn=DETECT_CHN)
            candidates = find_candidates(detect_img)
            target = tracker.update(candidates)
        else:
            target = tracker.last_target
        draw_target(img, target, clock.fps())
        send_target(target)
        Display.show_image(img)

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
