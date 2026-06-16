import os


SEARCH_ROOTS = ["/sdcard", "/data"]
MAX_DEPTH = 5


def safe_list(path):
    try:
        return os.listdir(path)
    except Exception:
        return []


def walk(path, depth, suffixes, found):
    if depth < 0:
        return
    for name in safe_list(path):
        if path != "/":
            full = path + "/" + name
        else:
            full = "/" + name
        low = name.lower()
        matched = False
        for suffix in suffixes:
            if low.endswith(suffix):
                matched = True
                break
        if matched:
            found.append(full)
        if depth > 0:
            walk(full, depth - 1, suffixes, found)


def main():
    usable_roots = []
    for root in SEARCH_ROOTS:
        items = safe_list(root)
        if items:
            usable_roots.append(root)

    if not usable_roots:
        print("No /sdcard or /data contents found.")
        print("Run this script on the K230 board, not on desktop Python.")
        return

    kmodels = []
    py_examples = []
    for root in usable_roots:
        walk(root, MAX_DEPTH, [".kmodel"], kmodels)
        walk(root, MAX_DEPTH, [".py"], py_examples)

    print("KMODELS:")
    for item in kmodels:
        print("  ", item)

    print("YOLO_PY_EXAMPLES:")
    for item in py_examples:
        low = item.lower()
        if "yolo" in low or "detect" in low or "seg" in low or "pose" in low:
            print("  ", item)


main()
