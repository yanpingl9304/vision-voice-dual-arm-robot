"""
ArUco Pose Estimation Module (Single Image)

Description:
Detect ArUco markers and estimate their 3D pose.

Input:
- Single RGB image

Output:
[
  {
    "id": int,
    "rvec": [rx, ry, rz],
    "tvec": [x, y, z]
  }
]

Coordinate System:
- Camera coordinate system
- x: right
- y: down
- z: forward (away from camera)

Unit:
- meters

Note:
- Requires camera calibration parameters
"""

import cv2
import numpy as np
import json

# =========================
# CONFIGURATION
# =========================

MARKER_LENGTH = 0.02  # meters

camera_matrix = np.array([
        [924.07073975, 0.0, 643.87634277],
        [0.0, 921.46142578, 346.78930664],
        [0.0, 0.0, 1.0]
], dtype=np.float32)

dist_coeffs = np.zeros((5, 1))

aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_5X5_50)
detector = cv2.aruco.ArucoDetector(aruco_dict)


# =========================
# Pose Estimation
# =========================

def detect_markers(image):
    """
    Detect ArUco markers and estimate their pose
    Returns:
        List[dict]: [{"id": int, "rvec": [rx, ry, rz], "tvec": [x, y, z]}, ...]
    """
    corners, ids, _ = detector.detectMarkers(image)
    if ids is None:
        return []

    results = []
    for i in range(len(ids)):
        marker_id = int(ids[i][0])
        img_points = corners[i][0].astype(np.float32)

        half = MARKER_LENGTH / 2
        obj_points = np.array([
            [-half,  half, 0],
            [ half,  half, 0],
            [ half, -half, 0],
            [-half, -half, 0]
        ], dtype=np.float32)

        success, rvec, tvec = cv2.solvePnP(
            obj_points,
            img_points,
            camera_matrix,
            dist_coeffs
        )
        if not success:
            continue

        rvec = np.array(rvec).reshape(3).tolist()
        tvec = np.array(tvec).reshape(3).tolist()

        results.append({
            "id": marker_id,
            "rvec": rvec,
            "tvec": tvec
        })
    return results


# =========================
# Debug Visualization
# =========================

def draw_markers(image):
    corners, ids, _ = detector.detectMarkers(image)
    img = image.copy()
    if ids is not None:
        cv2.aruco.drawDetectedMarkers(img, corners, ids)
    return img

# =========================
# CLI Test
# =========================

if __name__ == "__main__":
    IMAGE_PATH = "aruco_test.jpg"
    image = cv2.imread(IMAGE_PATH)
    if image is None:
        raise ValueError("Image not found")
    markers = detect_markers(image)

    print(json.dumps(markers, indent=2))

    debug_img = draw_markers(image)
    cv2.imshow("aruco", debug_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
