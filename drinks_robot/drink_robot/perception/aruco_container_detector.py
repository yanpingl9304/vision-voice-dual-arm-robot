from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class ContainerDetection:
    marker_id: int
    rvec: np.ndarray
    tvec: np.ndarray


class ArucoContainerDetector:
    """ArUco detector used by right arm to recognize drink containers."""

    def __init__(
        self,
        camera_matrix: np.ndarray,
        distortion: np.ndarray,
        marker_length: float = 0.02,
        dictionary_id: int = cv2.aruco.DICT_5X5_50,
    ):
        self.camera_matrix = camera_matrix.astype(np.float64)
        self.distortion = distortion.astype(np.float64)
        self.marker_length = marker_length
        self.dictionary = cv2.aruco.getPredefinedDictionary(dictionary_id)
        self.detector = cv2.aruco.ArucoDetector(self.dictionary)

    def detect(self, image_bgr: np.ndarray, allowed_ids: Optional[Iterable[int]] = None) -> List[ContainerDetection]:
        corners, ids, _ = self.detector.detectMarkers(image_bgr)
        if ids is None:
            return []

        ids_flat = ids.flatten().tolist()
        allowed = set(allowed_ids) if allowed_ids is not None else None
        detections: List[ContainerDetection] = []

        for marker_id, corner in zip(ids_flat, corners):
            if allowed is not None and marker_id not in allowed:
                continue
            retval, rvec, tvec = cv2.solvePnP(
                objectPoints=self._object_points(),
                imagePoints=corner.astype(np.float32),
                cameraMatrix=self.camera_matrix,
                distCoeffs=self.distortion,
                flags=cv2.SOLVEPNP_IPPE_SQUARE,
            )
            if not retval:
                continue
            detections.append(
                ContainerDetection(marker_id=marker_id, rvec=rvec.flatten(), tvec=tvec.flatten())
            )

        return detections

    def draw_detections(
        self, image_bgr: np.ndarray, detections: List[ContainerDetection]
    ) -> np.ndarray:
        """Draw projected marker corners, IDs, and XYZ axes for each detection."""
        img_vis = image_bgr.copy()
        obj_pts = self._object_points()
        axis_3d = np.array(
            [[self.marker_length, 0, 0], [0, self.marker_length, 0], [0, 0, self.marker_length]],
            dtype=np.float32,
        )
        origin_3d = np.zeros((1, 3), dtype=np.float32)

        for detection in detections:
            # --- 關鍵修正：確保 rvec 和 tvec 是符合 OpenCV 要求 的 (3, 1) 形狀與型態 ---
            rvec = np.array(detection.rvec, dtype=np.float32).reshape(-1, 1)
            tvec = np.array(detection.tvec, dtype=np.float32).reshape(-1, 1)
            # -----------------------------------------------------------------

            imgpts, _ = cv2.projectPoints(
                obj_pts, rvec, tvec, self.camera_matrix, self.distortion
            )
            imgpts = np.int32(imgpts).reshape(-1, 2)
            cv2.polylines(img_vis, [imgpts], True, (0, 255, 0), 2)
            cv2.putText(
                img_vis,
                f'ID:{detection.marker_id}',
                tuple(imgpts[0]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )

            # 這裡也同步改用標準化後的 rvec 和 tvec
            axis_pts, _ = cv2.projectPoints(
                axis_3d, rvec, tvec, self.camera_matrix, self.distortion
            )
            origin_pt, _ = cv2.projectPoints(
                origin_3d, rvec, tvec, self.camera_matrix, self.distortion
            )
            origin_pt = tuple(np.int32(origin_pt).ravel())
            axis_pts = np.int32(axis_pts).reshape(-1, 2)
            cv2.line(img_vis, origin_pt, tuple(axis_pts[0]), (0, 0, 255), 2)
            cv2.line(img_vis, origin_pt, tuple(axis_pts[1]), (0, 255, 0), 2)
            cv2.line(img_vis, origin_pt, tuple(axis_pts[2]), (255, 0, 0), 2)

        return img_vis

    def _object_points(self) -> np.ndarray:
        half = self.marker_length / 2.0
        return np.array(
            [
                [-half, half, 0.0],
                [half, half, 0.0],
                [half, -half, 0.0],
                [-half, -half, 0.0],
            ],
            dtype=np.float32,
        )
