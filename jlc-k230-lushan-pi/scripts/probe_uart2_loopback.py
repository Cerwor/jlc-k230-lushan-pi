import time

from machine import FPIOA, Pin, UART


UART_BAUDRATE = 115200
LOOPBACK_PAIRS = (
    (5, 6),
    (11, 12),
    (44, 45),
)
GPIO_SCAN_LOOPS = 8
UART_LOOPS = 80


uart = None


def gpio_func(pin_num):
    return getattr(FPIOA, "GPIO%d" % pin_num)


def make_input(pin_num):
    try:
        return Pin(pin_num, Pin.IN, pull=Pin.PULL_DOWN)
    except Exception:
        return Pin(pin_num, Pin.IN, pull=Pin.PULL_NONE)


def scan_pair(tx_pin, rx_pin):
    fpioa = FPIOA()
    fpioa.set_function(tx_pin, gpio_func(tx_pin))
    fpioa.set_function(rx_pin, gpio_func(rx_pin))
    out_pin = Pin(tx_pin, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
    in_pin = make_input(rx_pin)

    matched = 0
    saw_low = False
    saw_high = False
    for i in range(GPIO_SCAN_LOOPS):
        value = i % 2
        out_pin.value(value)
        time.sleep_ms(40)
        read_value = in_pin.value()
        if read_value == value:
            matched += 1
        if read_value == 0:
            saw_low = True
        if read_value == 1:
            saw_high = True

    print("UART2_SCAN_PAIR tx=%d rx=%d matched=%d saw_low=%d saw_high=%d" %
          (tx_pin, rx_pin, matched, int(saw_low), int(saw_high)))
    if matched == GPIO_SCAN_LOOPS and saw_low and saw_high:
        return True
    return False


def find_loopback_pair():
    for i in range(len(LOOPBACK_PAIRS)):
        pair = LOOPBACK_PAIRS[i]
        try:
            if scan_pair(pair[0], pair[1]):
                return pair
        except Exception as e:
            print("UART2_SCAN_PAIR_ERROR tx=%d rx=%d err=%s" %
                  (pair[0], pair[1], e))
    return None


def run_uart_loopback(tx_pin, rx_pin):
    global uart
    fpioa = FPIOA()
    fpioa.set_function(tx_pin, FPIOA.UART2_TXD)
    fpioa.set_function(rx_pin, FPIOA.UART2_RXD)
    uart = UART(UART.UART2, baudrate=UART_BAUDRATE,
                bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
                stop=UART.STOPBITS_ONE)

    rx_count = 0
    tx_count = 0
    total_bytes = 0
    uart.write("UART2 loopback probe start\r\n")
    for i in range(UART_LOOPS):
        if i % 20 == 0:
            uart.write("ping,%d\r\n" % i)
            tx_count += 1
        data = uart.read()
        if data:
            rx_count += 1
            total_bytes += len(data)
            print("UART2_LOOPBACK_RX:", data)
        time.sleep_ms(25)
    print("UART2_LOOPBACK_DONE tx_pin=%d rx_pin=%d tx=%d rx=%d bytes=%d" %
          (tx_pin, rx_pin, tx_count, rx_count, total_bytes))


try:
    print("UART2_LOOPBACK_PROBE_START")
    pair = find_loopback_pair()
    if not pair:
        print("UART2_LOOPBACK_NO_LINK")
    else:
        print("UART2_LOOPBACK_PAIR tx=%d rx=%d" % (pair[0], pair[1]))
        run_uart_loopback(pair[0], pair[1])
    print("UART2_LOOPBACK_PROBE_DONE")
except Exception as e:
    print("UART2_LOOPBACK_PROBE_ERROR:", e)
finally:
    if uart:
        uart.deinit()
