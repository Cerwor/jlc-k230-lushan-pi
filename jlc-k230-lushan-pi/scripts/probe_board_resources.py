# @runtime: canmv
# @route: resource-discovery
# @requires: storage

import os


SEARCH_ROOTS = ["/sdcard", "/data"]
MAX_DEPTH = 4
MAX_DIRS = 120
MAX_CHILDREN_PER_DIR = 120
MAX_KMODELS = 80
MAX_PY_EXAMPLES = 120

dir_count = 0
truncated = 0


def safe_list(path):
    try:
        return os.listdir(path)
    except Exception:
        return []


def mark_truncated(reason):
    global truncated
    if not truncated:
        print("RESOURCE_TRUNCATED reason=%s" % reason)
    truncated = 1


def is_yolo_example(path):
    low = path.lower()
    if "yolo" in low:
        return True
    if "detect" in low:
        return True
    if "seg" in low:
        return True
    if "_pose" in low:
        return True
    if "pose_" in low:
        return True
    if "-pose" in low:
        return True
    if "pose-" in low:
        return True
    return False


def walk_collect(path, depth, kmodels, py_examples):
    global dir_count
    global truncated

    if depth < 0:
        return
    if truncated:
        return
    if dir_count >= MAX_DIRS:
        mark_truncated("max_dirs")
        return

    items = safe_list(path)
    dir_count += 1
    if dir_count == 1 or (dir_count % 20) == 0:
        print("RESOURCE_SCAN dirs=%d path=%s" % (dir_count, path))

    child_count = 0
    for name in items:
        child_count += 1
        if child_count > MAX_CHILDREN_PER_DIR:
            mark_truncated("max_children")
            break

        if path != "/":
            full = path + "/" + name
        else:
            full = "/" + name

        low = name.lower()

        if low.endswith(".kmodel"):
            if len(kmodels) < MAX_KMODELS:
                kmodels.append(full)
            else:
                mark_truncated("max_kmodels")

        if low.endswith(".py"):
            if is_yolo_example(full):
                if len(py_examples) < MAX_PY_EXAMPLES:
                    py_examples.append(full)
                else:
                    mark_truncated("max_py_examples")

        should_recurse = False
        if depth > 0:
            if "." not in name:
                should_recurse = True
        if should_recurse:
            walk_collect(full, depth - 1, kmodels, py_examples)
        if truncated:
            break


def main():
    print("RESOURCE_PROBE_START max_depth=%d max_dirs=%d max_children=%d" % (MAX_DEPTH, MAX_DIRS, MAX_CHILDREN_PER_DIR))

    usable_roots = []
    for root in SEARCH_ROOTS:
        items = safe_list(root)
        if items:
            usable_roots.append(root)
            print("RESOURCE_ROOT %s items=%d" % (root, len(items)))

    if not usable_roots:
        print("No /sdcard or /data contents found.")
        print("Run this script on the K230 board, not on desktop Python.")
        return

    kmodels = []
    py_examples = []
    for root in usable_roots:
        walk_collect(root, MAX_DEPTH, kmodels, py_examples)

    print("KMODELS count=%d" % len(kmodels))
    for item in kmodels:
        print("  ", item)

    print("YOLO_PY_EXAMPLES count=%d" % len(py_examples))
    for item in py_examples:
        print("  ", item)

    print("RESOURCE_PROBE_DONE dirs=%d truncated=%d" % (dir_count, truncated))


main()
