# @runtime: canmv
# @route: model-runtime-discovery
# @requires: storage

import os


SEARCH_ROOTS = ("/sdcard/examples", "/sdcard", "/data")
MAX_DEPTH = 4
MAX_DIRS = 160
MAX_CHILDREN_PER_DIR = 120
MAX_KMODELS = 120
MAX_EXAMPLES = 120

dir_count = 0
truncated = 0
visited_paths = []


def safe_list(path):
    try:
        return os.listdir(path)
    except Exception:
        return []


def mark_truncated(reason):
    global truncated
    if not truncated:
        print("YOLO_PROBE_TRUNCATED reason=%s" % reason)
    truncated = 1


def is_yolo_example(path):
    low = path.lower()
    if "yolo" in low:
        return True
    if "object_detect" in low:
        return True
    if "detect" in low and "ai" in low:
        return True
    return False


def walk_collect(path, depth, kmodels, examples):
    global dir_count
    global truncated

    if depth < 0:
        return
    if truncated:
        return
    if path in visited_paths:
        return
    visited_paths.append(path)
    if dir_count >= MAX_DIRS:
        mark_truncated("max_dirs")
        return

    items = safe_list(path)
    dir_count += 1
    if dir_count == 1 or dir_count % 20 == 0:
        print("YOLO_PROBE_SCAN dirs=%d path=%s" % (dir_count, path))

    child_count = 0
    for name in items:
        child_count += 1
        if child_count > MAX_CHILDREN_PER_DIR:
            mark_truncated("max_children")
            break

        if path == "/":
            full = "/" + name
        else:
            full = path + "/" + name
        low = name.lower()

        if low.endswith(".kmodel"):
            if len(kmodels) < MAX_KMODELS:
                kmodels.append(full)
            else:
                mark_truncated("max_kmodels")

        if low.endswith(".py") and is_yolo_example(full):
            if len(examples) < MAX_EXAMPLES:
                examples.append(full)
            else:
                mark_truncated("max_examples")

        if depth > 0 and "." not in name:
            walk_collect(full, depth - 1, kmodels, examples)
        if truncated:
            break


def import_flag(label, import_func):
    try:
        import_func()
        print("YOLO_IMPORT %s=1" % label)
        return 1
    except Exception as e:
        print("YOLO_IMPORT %s=0 err=%s" % (label, e))
        return 0


def import_nncase():
    import nncase_runtime
    return nncase_runtime


def import_aicube():
    import aicube
    return aicube


def import_pipeline():
    from libs.PipeLine import PipeLine
    return PipeLine


def import_yolo5():
    from libs.YOLO import YOLOv5
    return YOLOv5


def import_yolo8():
    from libs.YOLO import YOLOv8
    return YOLOv8


def import_yolo11():
    from libs.YOLO import YOLO11
    return YOLO11


def main():
    print("YOLO_PROBE_START")

    nncase_ok = import_flag("nncase", import_nncase)
    aicube_ok = import_flag("aicube", import_aicube)
    pipeline_ok = import_flag("pipeline", import_pipeline)
    yolo5_ok = import_flag("yolo5", import_yolo5)
    yolo8_ok = import_flag("yolo8", import_yolo8)
    yolo11_ok = import_flag("yolo11", import_yolo11)

    kmodels = []
    examples = []
    root_count = 0
    for root in SEARCH_ROOTS:
        items = safe_list(root)
        if items:
            root_count += 1
            print("YOLO_ROOT %s items=%d" % (root, len(items)))
            walk_collect(root, MAX_DEPTH, kmodels, examples)

    print("YOLO_KMODELS count=%d" % len(kmodels))
    for item in kmodels:
        print("  ", item)

    print("YOLO_EXAMPLES count=%d" % len(examples))
    for item in examples:
        print("  ", item)

    print("YOLO_PROBE_DONE nncase=%d aicube=%d pipeline=%d yolo5=%d yolo8=%d yolo11=%d roots=%d kmodels=%d examples=%d dirs=%d truncated=%d" % (
        nncase_ok, aicube_ok, pipeline_ok, yolo5_ok, yolo8_ok, yolo11_ok,
        root_count, len(kmodels), len(examples), dir_count, truncated))


try:
    main()
except Exception as e:
    print("YOLO_PROBE_ERROR", e)
