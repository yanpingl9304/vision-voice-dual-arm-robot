"""
Cup OBB Sorting Module (Single Image)

Description:
This module performs cup detection using a YOLO-OBB model and assigns
a picking order based on spatial rules.

Input:
- Single RGB image

Output:
[
  {
    "id": int,
    "obb": [x1,y1,x2,y2,x3,y3,x4,y4]
  },
  ...
]

VERTICAL_ORDER:
   - "bottom": sort from bottom to top (y large → small)
   - "top": sort from top to bottom (y small → large)

HORIZONTAL_PRIORITY:
   - "left": select object with NO object on its left
   - "right": select object with NO object on its right
"""

import cv2
import numpy as np
import json
from ultralytics import YOLO


# =========================
# CONFIGURATION
# =========================

VERTICAL_ORDER = "bottom"   # "bottom" or "top"
HORIZONTAL_PRIORITY = "left"  # "left" or "right"
CONF_THRESHOLD = 0.5


# =========================
# Geometry
# =========================

def polygon_area(xs, ys):
    area = 0
    n = len(xs)
    for i in range(n):
        j = (i + 1) % n
        area += xs[i] * ys[j]
        area -= xs[j] * ys[i]
    return abs(area) / 2


def obb_features(obb):
    if isinstance(obb[0], list):
        pts = obb
    else:
        pts = [(obb[i], obb[i+1]) for i in range(0, 8, 2)]
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    cx = sum(xs) / 4
    cy = sum(ys) / 4

    pts_sorted_by_x = sorted(pts, key=lambda p: p[0])
    left_pts = pts_sorted_by_x[:2]
    right_pts = pts_sorted_by_x[-2:]
    left_y_range = (min(p[1] for p in left_pts), max(p[1] for p in left_pts))
    right_y_range = (min(p[1] for p in right_pts), max(p[1] for p in right_pts))

    return {
        "center": (cx, cy),
        "y_range": (min(ys), max(ys)),
        "left_y_range": left_y_range,
        "right_y_range": right_y_range,
        "x_min": min(xs),
        "x_max": max(xs),
        "area": polygon_area(xs, ys)
    }


def has_horizontal_neighbor(target, others):
    if HORIZONTAL_PRIORITY == "left":
        ty_min, ty_max = target["left_y_range"]
    else:
        ty_min, ty_max = target["right_y_range"]

    for obj in others:
        oy_min, oy_max = obj["y_range"]
        overlap = not (oy_max < ty_min or oy_min > ty_max)
        if not overlap:
            continue
        if HORIZONTAL_PRIORITY == "left":
            if obj["x_min"] < target["x_min"]:
                return True
        elif HORIZONTAL_PRIORITY == "right":
            if obj["x_max"] > target["x_max"]:
                return True
    return False


# =========================
# Sorting
# =========================

def sort_cups(detections):
    objs = []
    for det in detections:
        feat = obb_features(det["obb"])
        objs.append({
            "obb": det["obb"],
            "confidence": det["confidence"],
            **feat
        })
    result = []
    remaining = objs.copy()
    order_id = 1

    while remaining:
        # Vertical sorting
        if VERTICAL_ORDER == "bottom":
            remaining.sort(key=lambda o: o["center"][1], reverse=True)
        elif VERTICAL_ORDER == "top":
            remaining.sort(key=lambda o: o["center"][1])

        selected = None
        for i, candidate in enumerate(remaining):
            others = remaining[:i] + remaining[i+1:]

            if not has_horizontal_neighbor(candidate, others):
                selected = candidate
                break
        # fallback
        if selected is None:
            selected = max(remaining, key=lambda o: o["area"])

        selected["id"] = order_id
        result.append(selected)

        remaining.remove(selected)
        order_id += 1
    return result


# =========================
# YOLO Inference
# =========================

def detect_cups(model, image):
    results = model(image)[0]
    detections = []
    if results.obb is None:
        return detections
    for r in results.obb:
        conf = float(r.conf[0])
        if conf < CONF_THRESHOLD:
            continue
        pts = r.xyxyxyxy[0].tolist()
        obb = [coord for p in pts for coord in p]
        detections.append({
            "obb": obb,
            "confidence": conf
        })
    return detections


# =========================
# Main API
# =========================

def process_image(model, image):
    detections = detect_cups(model, image)
    sorted_objs = sort_cups(detections)
    return [
        {
            "id": obj["id"],
            "obb": obj["obb"]
        }
        for obj in sorted_objs
    ]


# =========================
# Debug Visualization
# =========================

def draw_result(image, sorted_objs):
    img = image.copy()
    for obj in sorted_objs:
        pts = np.array(obj["obb"], dtype=np.int32).reshape(-1, 2)
        cv2.polylines(img, [pts], True, (0, 255, 0), 2)
        cx, cy = map(int, obj["center"])
        cv2.putText(img, str(obj["id"]), (cx, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    return img


# =========================
# CLI Test
# =========================

if __name__ == "__main__":
    MODEL_PATH = "cup.pt"
    IMAGE_PATH = "cup_test.png"

    model = YOLO(MODEL_PATH)
    image = cv2.imread(IMAGE_PATH)

    if image is None:
        raise ValueError("Image not found")

    detections = detect_cups(model, image)
    sorted_objs = sort_cups(detections)

    output = [
        {"id": obj["id"], "obb": obj["obb"]}
        for obj in sorted_objs
    ]

    print(json.dumps(output, indent=2))

    debug_img = draw_result(image, sorted_objs)
    cv2.imshow("result", debug_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
