# @runtime: canmv
# @route: actuator-smoke
# @requires: gpio,pwm,timer

import time

from machine import FPIOA, Pin, PWM, Timer


LASER_PIN = 33
SERVO_PWM_PIN = 46
SERVO_PWM_FUNC = "PWM2"
SERVO_PWM_CHANNEL = 2

STEPPER_PINS = [15, 17, 16, 19]
BUTTON_PIN = 53

SERVO_FREQ = 50
SERVO_MIN_MS = 0.5
SERVO_MAX_MS = 2.5
SERVO_PERIOD_MS = 20.0


fpioa = FPIOA()
fpioa.set_function(LASER_PIN, FPIOA.GPIO33)
fpioa.set_function(SERVO_PWM_PIN, getattr(FPIOA, SERVO_PWM_FUNC))
for pin in STEPPER_PINS:
    fpioa.set_function(pin, getattr(FPIOA, "GPIO%d" % pin))
fpioa.set_function(BUTTON_PIN, FPIOA.GPIO53)

laser = Pin(LASER_PIN, Pin.OUT)
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_DOWN)
servo = PWM(SERVO_PWM_CHANNEL, SERVO_FREQ)
servo.enable(1)

motor_pins = []
for pin in STEPPER_PINS:
    motor_pins.append(Pin(pin, Pin.OUT))
step_status = [[1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 1], [1, 0, 0, 1]]
step_index = 0
step_dir = 0


def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value


def servo_write_ratio(ratio):
    ratio = clamp(ratio, 0.0, 1.0)
    pulse_ms = SERVO_MIN_MS + (SERVO_MAX_MS - SERVO_MIN_MS) * ratio
    servo.duty(pulse_ms / SERVO_PERIOD_MS * 100)


def stepper_stop():
    for pin in motor_pins:
        pin.value(0)


def stepper_callback(timer):
    global step_index
    if step_dir == 0:
        return
    step_index = (step_index + step_dir) % 4
    for i in range(len(motor_pins)):
        motor_pins[i].value(step_status[step_index][i])


timer = Timer(-1)

try:
    laser.value(0)
    servo_write_ratio(0.5)
    timer.init(period=5, mode=Timer.PERIODIC, callback=stepper_callback)

    mode = 0
    last_button = 0
    last_change = time.ticks_ms()

    while True:
        now = time.ticks_ms()
        value = button.value()
        if value == 1 and last_button == 0 and time.ticks_diff(now, last_change) > 300:
            mode = (mode + 1) % 4
            last_change = now
            print("mode:", mode)
        last_button = value

        if mode == 1 or mode == 3:
            laser.value(1)
        else:
            laser.value(0)

        if mode == 2:
            step_dir = 1
        elif mode == 3:
            step_dir = -1
        else:
            step_dir = 0
        servo_write_ratio((now % 2000) / 2000.0)
        time.sleep_ms(20)

finally:
    laser.value(0)
    step_dir = 0
    stepper_stop()
    servo_write_ratio(0.5)
    servo.deinit()
    timer.deinit()
