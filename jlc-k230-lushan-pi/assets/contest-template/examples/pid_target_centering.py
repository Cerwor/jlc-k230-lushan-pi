class IncrementalPID:
    def __init__(self, kp, ki, target=0, deadband=3, limit=200):
        self.kp = kp
        self.ki = ki
        self.target = target
        self.deadband = deadband
        self.limit = limit
        self.error_last = 0

    def clamp(self, value):
        if value > self.limit:
            return self.limit
        if value < -self.limit:
            return -self.limit
        return value

    def update(self, value):
        error = self.target - value
        if abs(error) <= self.deadband:
            self.error_last = error
            return 0
        delta = self.kp * (error - self.error_last) + self.ki * error
        self.error_last = error
        return int(self.clamp(delta))


def build_step_packet(motor_id, direction, steps):
    packet = [0xAA, 0xAA, motor_id & 0xFF, direction & 0xFF,
              (steps // 256) & 0xFF, steps & 0xFF, 0x00, 0xFF, 0xFF]
    packet[6] = sum(packet[2:6]) & 0xFF
    return bytes(packet)


def target_to_motor_packets(cx, cy, image_w=800, image_h=480):
    pid_x = IncrementalPID(0.4, 0.02, target=image_w // 2)
    pid_y = IncrementalPID(0.4, 0.02, target=image_h // 2)
    dx = pid_x.update(cx)
    dy = pid_y.update(cy)
    packets = []
    if dx:
        if dx > 0:
            dir_x = 1
        else:
            dir_x = 0
        packets.append(build_step_packet(1, dir_x, abs(dx)))
    if dy:
        if dy > 0:
            dir_y = 1
        else:
            dir_y = 0
        packets.append(build_step_packet(2, dir_y, abs(dy)))
    return packets
