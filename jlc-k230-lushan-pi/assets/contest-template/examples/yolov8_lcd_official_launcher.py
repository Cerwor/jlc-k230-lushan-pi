# Runs the official YOLOv8 object detection example on the 3.1-inch LCD.
# Use after verifying that this file exists on the board:
# /sdcard/examples/05-AI-Demo/object_detect_yolov8n.py

path = "/sdcard/examples/05-AI-Demo/object_detect_yolov8n.py"
code = open(path).read()
code = code.replace('display_mode="hdmi"', 'display_mode="lcd"')
code = code.replace("display_mode='hdmi'", "display_mode='lcd'")
code = code.replace('display_mode = "hdmi"', 'display_mode = "lcd"')
code = code.replace("display_mode = 'hdmi'", "display_mode = 'lcd'")
exec(code)
