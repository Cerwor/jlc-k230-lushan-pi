import gc
import os
import time


# =========================
# Project configuration
# =========================

PROJECT_NAME = "k230_contest_template"

DISPLAY_MODE = "lcd"        # "lcd", "virt", or "hdmi"
DISPLAY_WIDTH = 800
DISPLAY_HEIGHT = 480
RGB888P_SIZE = [640, 360]

USE_YOLO = False             # False: camera LCD preview; True: YOLO video pipeline
YOLO_FAMILY = "YOLOv8"       # "YOLOv5", "YOLOv8", or "YOLO11"
YOLO_TASK = "detect"         # "classify", "detect", or "segment"
KMODEL_PATH = "/data/best.kmodel"
LABELS = ["target"]
MODEL_INPUT_SIZE = [320, 320]
CONF_THRESH = 0.50
NMS_THRESH = 0.45
MASK_THRESH = 0.50
MAX_BOXES_NUM = 10

ENABLE_UART = False
UART_ID = 2
UART_TX_PIN = 11
UART_RX_PIN = 12
UART_BAUDRATE = 115200

ENABLE_PWM_SAFE_OUTPUT = False
PWM_PIN = 42
PWM_FUNC_NAME = "PWM0"
PWM_CHANNEL = 0
PWM_FREQ = 50
PWM_NEUTRAL_DUTY_U16 = 0
PWM_MIN_DUTY_U16 = 0
PWM_MAX_DUTY_U16 = 65535

TARGET_TIMEOUT_MS = 500
GC_INTERVAL_FRAMES = 30
RUNTIME_ERROR_LIMIT = 3
RECOVERY_PAUSE_MS = 300
MAX_RECOVERY_COUNT = 3


# =========================
# Runtime state
# =========================

sensor = None
uart = None
pwm = None
pl = None
yolo = None
frame_id = 0
last_target_ms = 0
last_result = None
recovery_count = 0


def ticks_ms():
    return time.ticks_ms()


def ticks_diff(new, old):
    return time.ticks_diff(new, old)


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def display_size_for_mode():
    if DISPLAY_MODE == "lcd":
        return [800, 480]
    if DISPLAY_MODE == "hdmi":
        return [1920, 1080]
    return [DISPLAY_WIDTH, DISPLAY_HEIGHT]


def init_uart():
    global uart
    if not ENABLE_UART:
        return None

    from machine import FPIOA, UART

    fpioa = FPIOA()
    if UART_ID == 2:
        fpioa.set_function(UART_TX_PIN, FPIOA.UART2_TXD)
        fpioa.set_function(UART_RX_PIN, FPIOA.UART2_RXD)
        uart_obj = UART(UART.UART2, baudrate=UART_BAUDRATE,
                        bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
                        stop=UART.STOPBITS_ONE)
    elif UART_ID == 3:
        fpioa.set_function(UART_TX_PIN, FPIOA.UART3_TXD)
        fpioa.set_function(UART_RX_PIN, FPIOA.UART3_RXD)
        uart_obj = UART(UART.UART3, baudrate=UART_BAUDRATE,
                        bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
                        stop=UART.STOPBITS_ONE)
    else:
        raise ValueError("Use UART2 or UART3 for contest peripherals")

    uart = uart_obj
    uart.write("k230 contest uart ready\r\n")
    return uart


def init_pwm_safe_output():
    global pwm
    if not ENABLE_PWM_SAFE_OUTPUT:
        return None

    from machine import FPIOA, PWM

    fpioa = FPIOA()
    pwm_func = getattr(FPIOA, PWM_FUNC_NAME)
    fpioa.set_function(PWM_PIN, pwm_func)

    pwm_obj = PWM(PWM_CHANNEL)
    pwm_obj.freq(PWM_FREQ)
    pwm_obj.duty_u16(PWM_NEUTRAL_DUTY_U16)
    pwm = pwm_obj
    return pwm


def set_pwm_output(duty_u16):
    if pwm is None:
        return
    safe = clamp(duty_u16, PWM_MIN_DUTY_U16, PWM_MAX_DUTY_U16)
    pwm.duty_u16(safe)


def safe_stop_outputs(reason):
    set_pwm_output(PWM_NEUTRAL_DUTY_U16)
    if uart is not None:
        uart.write("STATE:SAFE_STOP,REASON:%s\r\n" % reason)


def init_preview_camera_lcd():
    global sensor
    from media.sensor import Sensor
    from media.display import Display
    from media.media import MediaManager

    sensor = Sensor()
    sensor.reset()
    sensor.set_framesize(sensor.WVGA)
    sensor.set_pixformat(Sensor.RGB565)

    if DISPLAY_MODE == "lcd":
        Display.init(Display.ST7701, width=800, height=480, to_ide=True)
    elif DISPLAY_MODE == "hdmi":
        Display.init(Display.LT9611, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, to_ide=True)
    else:
        Display.init(Display.VIRT, width=DISPLAY_WIDTH, height=DISPLAY_HEIGHT, fps=60)

    MediaManager.init()
    sensor.run()


def recover_preview_camera_lcd(reason):
    global sensor, recovery_count
    from media.display import Display
    from media.media import MediaManager

    safe_stop_outputs(reason)
    recovery_count += 1
    print("recover preview:", reason, recovery_count)

    if recovery_count > MAX_RECOVERY_COUNT:
        raise RuntimeError("too many preview recoveries")

    try:
        if sensor is not None:
            sensor.stop()
    except Exception as e:
        print("sensor recover stop error:", e)

    try:
        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        MediaManager.deinit()
    except Exception as e:
        print("media recover deinit error:", e)

    sensor = None
    gc.collect()
    time.sleep_ms(RECOVERY_PAUSE_MS)
    init_preview_camera_lcd()


def init_yolo_pipeline():
    global pl, yolo

    from libs.PipeLine import PipeLine
    from libs.YOLO import YOLOv5, YOLOv8, YOLO11

    display_size = display_size_for_mode()
    pl = PipeLine(rgb888p_size=RGB888P_SIZE,
                  display_size=display_size,
                  display_mode=DISPLAY_MODE)
    pl.create()

    if YOLO_FAMILY == "YOLOv5":
        yolo_cls = YOLOv5
    elif YOLO_FAMILY == "YOLOv8":
        yolo_cls = YOLOv8
    else:
        yolo_cls = YOLO11

    kwargs = {}
    kwargs["task_type"] = YOLO_TASK
    kwargs["mode"] = "video"
    kwargs["kmodel_path"] = KMODEL_PATH
    kwargs["labels"] = LABELS
    kwargs["rgb888p_size"] = RGB888P_SIZE
    kwargs["model_input_size"] = MODEL_INPUT_SIZE
    kwargs["display_size"] = display_size
    kwargs["conf_thresh"] = CONF_THRESH
    kwargs["debug_mode"] = 0
    if YOLO_TASK in ("detect", "segment"):
        kwargs["nms_thresh"] = NMS_THRESH
        kwargs["max_boxes_num"] = MAX_BOXES_NUM
    if YOLO_TASK == "segment":
        kwargs["mask_thresh"] = MASK_THRESH

    yolo = yolo_cls(**kwargs)
    yolo.config_preprocess()


def init_hardware():
    print(PROJECT_NAME, "init")
    init_uart()
    init_pwm_safe_output()
    if USE_YOLO:
        init_yolo_pipeline()
    else:
        init_preview_camera_lcd()


def parse_target(result):
    # Keep this function small and project-specific.
    # Return a dict with found, cx, cy, score, label, and raw.
    if not result:
        return {"found": False, "raw": result}
    return {"found": True, "raw": result}


def decision_step(target):
    now = ticks_ms()
    if target.get("found"):
        return {"state": "TRACK", "pwm": PWM_NEUTRAL_DUTY_U16, "last_seen": now}
    if last_target_ms and ticks_diff(now, last_target_ms) > TARGET_TIMEOUT_MS:
        return {"state": "LOST", "pwm": PWM_NEUTRAL_DUTY_U16, "last_seen": last_target_ms}
    return {"state": "SEARCH", "pwm": PWM_NEUTRAL_DUTY_U16, "last_seen": last_target_ms}


def actuation_step(command):
    set_pwm_output(command.get("pwm", PWM_NEUTRAL_DUTY_U16))
    if uart is not None:
        msg = "STATE:%s,PWM:%s\r\n" % (command.get("state"), command.get("pwm"))
        uart.write(msg)


def telemetry_preview(img, clock):
    img.draw_string_advanced(20, 20, 48,
                             "FPS:%d" % int(clock.fps()),
                             color=(255, 0, 0))
    img.draw_string_advanced(20, 80, 40,
                             "MODE:PREVIEW",
                             color=(255, 255, 0))


def run_preview_loop():
    global frame_id
    from media.sensor import CAM_CHN_ID_0
    from media.display import Display

    clock = time.clock()
    frame_errors = 0
    while True:
        try:
            os.exitpoint()
            clock.tick()
            img = sensor.snapshot(chn=CAM_CHN_ID_0)
            telemetry_preview(img, clock)
            Display.show_image(img)
            frame_id += 1
            frame_errors = 0
            if frame_id % GC_INTERVAL_FRAMES == 0:
                gc.collect()
        except Exception as e:
            print("preview frame error:", e)
            frame_errors += 1
            safe_stop_outputs("PREVIEW_FRAME_ERROR")
            if frame_errors >= RUNTIME_ERROR_LIMIT:
                recover_preview_camera_lcd("PREVIEW_FRAME_ERROR")
                frame_errors = 0
            else:
                time.sleep_ms(RECOVERY_PAUSE_MS)


def run_yolo_loop():
    global frame_id, last_result, last_target_ms
    from libs.PipeLine import ScopedTiming

    frame_errors = 0
    while True:
        try:
            os.exitpoint()
            with ScopedTiming("total", 1):
                img = pl.get_frame()

                if frame_id % 2 == 0:
                    last_result = yolo.run(img)

                target = parse_target(last_result)
                if target.get("found"):
                    last_target_ms = ticks_ms()

                command = decision_step(target)
                actuation_step(command)

                if last_result is not None:
                    yolo.draw_result(last_result, pl.osd_img)
                pl.osd_img.draw_string(5, 5, "STATE:%s" % command.get("state"),
                                       color=(255, 0, 0), scale=3)
                pl.show_image()

                frame_id += 1
                frame_errors = 0
                if frame_id % GC_INTERVAL_FRAMES == 0:
                    gc.collect()
        except Exception as e:
            print("yolo frame error:", e)
            frame_errors += 1
            safe_stop_outputs("YOLO_FRAME_ERROR")
            if frame_errors >= RUNTIME_ERROR_LIMIT:
                raise
            time.sleep_ms(RECOVERY_PAUSE_MS)


def cleanup():
    global sensor, uart, pwm, pl, yolo
    print(PROJECT_NAME, "cleanup")

    try:
        if pwm is not None:
            set_pwm_output(PWM_NEUTRAL_DUTY_U16)
            pwm.deinit()
    except Exception as e:
        print("pwm cleanup error:", e)

    try:
        if uart is not None:
            uart.write("k230 contest stop\r\n")
            uart.deinit()
    except Exception as e:
        print("uart cleanup error:", e)

    if USE_YOLO:
        try:
            if yolo is not None:
                yolo.deinit()
        except Exception as e:
            print("yolo cleanup error:", e)
        try:
            if pl is not None:
                pl.destroy()
        except Exception as e:
            print("pipeline cleanup error:", e)
    else:
        try:
            if sensor is not None:
                sensor.stop()
        except Exception as e:
            print("sensor cleanup error:", e)
        try:
            from media.display import Display
            from media.media import MediaManager
            Display.deinit()
            os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
            time.sleep_ms(100)
            MediaManager.deinit()
        except Exception as e:
            print("media cleanup error:", e)


def main():
    init_hardware()
    if USE_YOLO:
        run_yolo_loop()
    else:
        run_preview_loop()


try:
    main()
except KeyboardInterrupt:
    print("user stopped")
except Exception as e:
    print("error:", e)
finally:
    cleanup()
