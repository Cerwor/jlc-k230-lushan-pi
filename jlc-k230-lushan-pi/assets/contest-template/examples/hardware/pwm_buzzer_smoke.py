# @runtime: canmv
# @route: pwm-smoke
# @requires: pwm

import time

from machine import FPIOA, PWM


PWM_PIN = 43
PWM_FUNC_NAME = "PWM1"
PWM_CHANNEL = 1

fpioa = FPIOA()
fpioa.set_function(PWM_PIN, getattr(FPIOA, PWM_FUNC_NAME))

pwm = PWM(PWM_CHANNEL)

try:
    for freq in (1000, 2000, 4000, 2000):
        pwm.freq(freq)
        pwm.duty_u16(32768)
        print("beep", freq)
        time.sleep_ms(250)
        pwm.duty_u16(0)
        time.sleep_ms(150)
finally:
    pwm.duty_u16(0)
    pwm.deinit()
