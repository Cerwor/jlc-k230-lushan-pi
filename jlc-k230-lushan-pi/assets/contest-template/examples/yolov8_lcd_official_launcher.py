# Runs the official YOLOv8 object detection example on the 3.1-inch LCD.
# Use after verifying that this file exists on the board:
# /sdcard/examples/05-AI-Demo/object_detect_yolov8n.py

import os


path = "/sdcard/examples/05-AI-Demo/object_detect_yolov8n.py"

try:
    os.stat(path)
except Exception as e:
    raise OSError("official YOLOv8 example not found: %s" % path)

code = open(path).read()
original_code = code

replacements = (
    ('display_mode="hdmi"', 'display_mode="lcd"'),
    ("display_mode='hdmi'", "display_mode='lcd'"),
    ('display_mode = "hdmi"', 'display_mode = "lcd"'),
    ("display_mode = 'hdmi'", "display_mode = 'lcd'"),
)

index = 0
while index < len(replacements):
    pair = replacements[index]
    code = code.replace(pair[0], pair[1])
    index += 1

if code == original_code:
    raise RuntimeError("display_mode hdmi pattern was not replaced; official example may have changed")

if 'display_mode="hdmi"' in code:
    raise RuntimeError("display_mode hdmi remains after replacement")
if "display_mode='hdmi'" in code:
    raise RuntimeError("display_mode hdmi remains after replacement")
if 'display_mode = "hdmi"' in code:
    raise RuntimeError("display_mode hdmi remains after replacement")
if "display_mode = 'hdmi'" in code:
    raise RuntimeError("display_mode hdmi remains after replacement")

exec(code)
