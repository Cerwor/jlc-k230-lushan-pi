import argparse
import sys
import time


DEFAULT_BAUD = 2000000
DEFAULT_VID = 0x1209
DEFAULT_PID = 0xABD1
RAW_REPL_ATTEMPTS = 3


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


def write_and_read(ser, data, window_s):
    ser.write(data)
    ser.flush()
    return read_available(ser, window_s)


def short_log(data):
    text = data.decode("utf-8", "replace")
    text = text.replace("\r", "\\r").replace("\n", "\\n")
    if len(text) > 500:
        return text[:500] + "..."
    return text


def enter_raw_repl(ser):
    log = []
    saw_bytes = False
    for attempt in range(1, RAW_REPL_ATTEMPTS + 1):
        log.append("attempt %d" % attempt)

        # Leave raw REPL if a previous run stopped there, then interrupt user code.
        data = write_and_read(ser, b"\x02", 0.25)
        if data:
            saw_bytes = True
            log.append("ctrl-b: " + short_log(data))

        data = write_and_read(ser, b"\x03\x03", 1.0)
        if data:
            saw_bytes = True
            log.append("ctrl-c: " + short_log(data))

        # Some firmware prints "MPY: soft reboot" before the ordinary prompt appears.
        if b"MPY: soft reboot" in data or b">>>" not in data:
            extra = read_available(ser, 1.0)
            if extra:
                saw_bytes = True
                data += extra
                log.append("post-reset: " + short_log(extra))

        banner = write_and_read(ser, b"\x01", 1.0)
        if b"raw REPL" in banner:
            sys.stdout.write(banner.decode("utf-8", "replace"))
            return
        if banner:
            saw_bytes = True
            log.append("ctrl-a: " + short_log(banner))

        time.sleep(0.3)

    sys.stderr.write("Failed to enter raw REPL.\n")
    sys.stderr.write("Handshake log:\n")
    for item in log:
        sys.stderr.write("  " + item + "\n")
    if not saw_bytes:
        sys.stderr.write("No serial bytes were received. Close CanMV IDE/serial terminals, reset or replug the board, and check --port/--baud.\n")
    raise SystemExit(1)


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
    completed = False
    while time.time() - start < timeout_s:
        chunk = ser.read(4096)
        if chunk:
            data.extend(chunk)
            text = data.decode("utf-8", "replace")
            if "Traceback" in text or "\x04\x04>" in text:
                completed = "\x04\x04>" in text
                time.sleep(0.2)
                data.extend(ser.read(4096))
                break
        else:
            time.sleep(0.05)
    output = data.decode("utf-8", "replace")
    if not completed:
        sys.stderr.write("Timed out before raw REPL completion marker.\n")
        if output:
            sys.stderr.write("Partial output:\n")
            sys.stderr.write(output)
            if not output.endswith("\n"):
                sys.stderr.write("\n")
        raise SystemExit(1)
    return output


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
