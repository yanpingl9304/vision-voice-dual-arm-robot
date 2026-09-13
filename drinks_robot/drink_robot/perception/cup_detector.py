from __future__ import annotations

from dataclasses import dataclass
import importlib
from typing import List, Sequence, Tuple

import cv2
import numpy as np


@dataclass(frozen=True)
class CupDetection:
    cup_id: int
    obb: Sequence[float]


class CupDetector:
    """YOLO-OBB cup detector with spatial sorting & perspective correction. Lazily imports ultralytics."""

    CONF_THRESHOLD = 0.5
    VERTICAL_ORDER = "bottom"     
    HORIZONTAL_PRIORITY = "right"
    PERSPECTIVE_OFFSET_RATIO = 0.06

    def __init__(self, model_path: str):
        self.model_path = model_path
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            ultralytics_module = importlib.import_module('ultralytics')
            self._model = ultralytics_module.YOLO(self.model_path)


    @staticmethod
    def _polygon_area(xs: List[float], ys: List[float]) -> float:
        area = 0.0
        n = len(xs)
        for i in range(n):
            j = (i + 1) % n
            area += xs[i] * ys[j]
            area -= xs[j] * ys[i]
        return abs(area) / 2.0

    @staticmethod
    def _obb_features(obb: List[float]) -> dict:
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
            "area": CupDetector._polygon_area(xs, ys)
        }

    @classmethod
    def _has_horizontal_neighbor(cls, target: dict, others: List[dict]) -> bool:
        if cls.HORIZONTAL_PRIORITY == "left":
            ty_min, ty_max = target["left_y_range"]
        else:
            ty_min, ty_max = target["right_y_range"]

        for obj in others:
            oy_min, oy_max = obj["y_range"]
            overlap = not (oy_max < ty_min or oy_min > ty_max)
            if not overlap:
                continue
            
            if cls.HORIZONTAL_PRIORITY == "left":
                if obj["x_min"] < target["x_min"]:
                    return True
            elif cls.HORIZONTAL_PRIORITY == "right":
                if obj["x_max"] > target["x_max"]:
                    return True
        return False

    @classmethod
    def _sort_cups(cls, raw_detections: List[dict]) -> List[dict]:
        objs = []
        for det in raw_detections:
            feat = cls._obb_features(det["obb"])
            objs.append({
                "obb": det["obb"],
                "confidence": det["confidence"],
                **feat
            })
        
        result = []
        remaining = objs.copy()
        order_id = 1

        while remaining:
            if cls.VERTICAL_ORDER == "bottom":
                remaining.sort(key=lambda o: o["center"][1], reverse=True)
            else:
                remaining.sort(key=lambda o: o["center"][1])

            selected = None
            for i, candidate in enumerate(remaining):
                others = remaining[:i] + remaining[i+1:]
                if not cls._has_horizontal_neighbor(candidate, others):
                    selected = candidate
                    break
            
            if selected is None:
                selected = max(remaining, key=lambda o: o["area"])

            selected["id"] = order_id
            result.append(selected)
            remaining.remove(selected)
            order_id += 1
            
        return result


    def detect(self, image_bgr: np.ndarray) -> List[CupDetection]:
        self._ensure_model()
        results = self._model(image_bgr)
        
        if not results:
            return []

        obb = getattr(results[0], 'obb', None)
        if obb is None or obb.xyxyxyxy is None:
            return []

        img_h, img_w = image_bgr.shape[:2]
        img_cx, img_cy = img_w / 2.0, img_h / 2.0

        raw_detections = []
        confidences = obb.conf.cpu().numpy()
        points_batch = obb.xyxyxyxy.cpu().numpy()
        
        for conf, points in zip(confidences, points_batch):
            if conf < self.CONF_THRESHOLD:
                continue
            flat_points = np.array(points, dtype=float).reshape(-1).tolist()
            raw_detections.append({"obb": flat_points, "confidence": float(conf)})

        if not raw_detections:
            return []

        sorted_objs = self._sort_cups(raw_detections)

        detections: List[CupDetection] = []
        for obj in sorted_objs:
            original_obb = obj["obb"]
            cup_cx = obj["center"][0]
            cup_cy = obj["center"][1]
            
            offset_x = (img_cx - cup_cx) * self.PERSPECTIVE_OFFSET_RATIO
            offset_y = (img_cy - cup_cy) * self.PERSPECTIVE_OFFSET_RATIO
            
            shifted_obb = []
            for i in range(0, 8, 2):
                shifted_obb.append(original_obb[i] + offset_x)
                shifted_obb.append(original_obb[i+1] + offset_y)

            detections.append(CupDetection(cup_id=obj["id"], obb=shifted_obb))

        return detections

    def detect_with_visualization(
        self, image_bgr: np.ndarray
    ) -> Tuple[List[CupDetection], np.ndarray]:
        detections = self.detect(image_bgr)
        vis_image = self._draw_detections(image_bgr, detections)
        return detections, vis_image

    def _draw_detections(
        self, image_bgr: np.ndarray, detections: List[CupDetection]
    ) -> np.ndarray:
        img_vis = image_bgr.copy()
        
        img_h, img_w = img_vis.shape[:2]
        img_cx, img_cy = int(img_w / 2.0), int(img_h / 2.0)
        cv2.drawMarker(img_vis, (img_cx, img_cy), (255, 0, 0), cv2.MARKER_CROSS, 20, 2)

        for detection in detections:
            obb = np.array(detection.obb, dtype=np.float32).reshape(4, 2)
            pts = np.int32(obb)
            
            cv2.polylines(img_vis, [pts], True, (255, 200, 0), 2, cv2.LINE_AA)
            center = pts.mean(axis=0)
            
            cv2.circle(img_vis, tuple(center.astype(int)), 5, (0, 0, 255), -1)
            
            cv2.putText(
                img_vis,
                f"Cup {detection.cup_id}",
                tuple(center.astype(int)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (0, 0, 255),
                2,
            )
        return img_vis