import argparse
import sys
import time


DEFAULT_BAUD = 2000000
DEFAULT_VID = 0x1209
DEFAULT_PID = 0xABD1


def require_serial():
    try:
        import serial
        import serial.tools.list_ports
    except Exception as exc:
        raise SystemExit("pyserial is required: python -m pip install pyserial") from exc
    return serial, serial.tools.list_ports


def autodetect_port(list_ports):
    matches = []
    for port in list_ports.comports():
        if port.vid == DEFAULT_VID and port.pid == DEFAULT_PID:
            matches.append(port.device)
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise SystemExit("No CanMV/K230 USB serial port found. Pass --port COMx.")
    raise SystemExit("Multiple CanMV/K230 ports found: %s. Pass --port COMx." % ", ".join(matches))


def read_available(ser, window_s=0.25):
    end = time.time() + window_s
    data = bytearray()
    while time.time() < end:
        chunk = ser.read(4096)
        if chunk:
            data.extend(chunk)
            end = time.time() + window_s
        else:
            time.sleep(0.02)
    return bytes(data)


def enter_raw_repl(ser):
    ser.write(b"\x03\x03")
    time.sleep(0.2)
    ser.reset_input_buffer()
    ser.write(b"\x01")
    time.sleep(0.2)
    banner = read_available(ser, 0.2)
    if b"raw REPL" not in banner:
        sys.stdout.write(banner.decode("utf-8", "replace"))
        raise SystemExit("Failed to enter raw REPL.")
    sys.stdout.write(banner.decode("utf-8", "replace"))


def run_code(ser, code, timeout_s, chunk_size):
    encoded = code.encode("utf-8")
    for index in range(0, len(encoded), chunk_size):
        ser.write(encoded[index:index + chunk_size])
        ser.flush()
        time.sleep(0.01)
    ser.write(b"\x04")
    ser.flush()

    data = bytearray()
    start = time.time()
    while time.time() - start < timeout_s:
        chunk = ser.read(4096)
        if chunk:
            data.extend(chunk)
            text = data.decode("utf-8", "replace")
            if "Traceback" in text or "\x04\x04>" in text:
                time.sleep(0.2)
                data.extend(ser.read(4096))
                break
        else:
            time.sleep(0.05)
    return data.decode("utf-8", "replace")


def main():
    parser = argparse.ArgumentParser(description="Run a CanMV MicroPython file through K230 raw REPL.")
    parser.add_argument("script", help="MicroPython .py file to execute from RAM")
    parser.add_argument("--port", help="Serial port such as COM14; auto-detects VID:PID 1209:ABD1 when omitted")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help="Serial baud rate, default 2000000")
    parser.add_argument("--timeout", type=float, default=30.0, help="Seconds to wait for output")
    parser.add_argument("--chunk-size", type=int, default=128, help="Write chunk size for raw REPL upload")
    args = parser.parse_args()

    serial, list_ports = require_serial()
    port = args.port or autodetect_port(list_ports)
    with open(args.script, "r", encoding="utf-8") as handle:
        code = handle.read()

    ser = serial.Serial(port, args.baud, timeout=0.2, write_timeout=5)
    try:
        enter_raw_repl(ser)
        output = run_code(ser, code, args.timeout, args.chunk_size)
        sys.stdout.write(output)
    finally:
        try:
            ser.write(b"\x03")
            time.sleep(0.1)
            ser.write(b"\x02")
        finally:
            ser.close()


if __name__ == "__main__":
    main()
