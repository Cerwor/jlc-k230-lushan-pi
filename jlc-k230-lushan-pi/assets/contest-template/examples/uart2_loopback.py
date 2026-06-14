import time

from machine import FPIOA, UART


UART_TX_PIN = 11
UART_RX_PIN = 12
UART_BAUDRATE = 115200

fpioa = FPIOA()
fpioa.set_function(UART_TX_PIN, FPIOA.UART2_TXD)
fpioa.set_function(UART_RX_PIN, FPIOA.UART2_RXD)

uart = UART(UART.UART2, baudrate=UART_BAUDRATE,
            bits=UART.EIGHTBITS, parity=UART.PARITY_NONE,
            stop=UART.STOPBITS_ONE)

try:
    uart.write("UART2 loopback ready\r\n")
    while True:
        data = uart.read()
        if data:
            print("rx:", data)
            uart.write("echo:")
            uart.write(data)
            uart.write("\r\n")
        time.sleep_ms(20)
finally:
    uart.deinit()
