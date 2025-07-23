import math
import os
import shutil
from pathlib import Path

import cv2
import numpy as np
import zxingcpp


def pix2np(pix):
    im = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, pix.n)
    im = np.ascontiguousarray(im[..., [2, 1, 0]])  # rgb to bgr
    return im


def threshold(orig, th):
    if th == 0:
        img = orig.copy()
    else:
        ret, img = cv2.threshold(orig, 255 * float(th) / 100, 255, cv2.THRESH_BINARY)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, thresh = cv2.threshold(gray, 200, 255, 1)

    return thresh


def get_patches(orig, ppm, size_mm, tolerance=0.25):
    # List for the patches
    patches = []

    # Find patches
    contours, h = cv2.findContours(orig, 1, 2)

    # Get other patches
    for cnt in contours:

        leng = cv2.arcLength(cnt, True)

        if leng < 0:
            continue

        approx = cv2.approxPolyDP(cnt, 0.01 * cv2.arcLength(cnt, True), True)

        if (len(approx) > 8) or (len(approx) < 4):
            continue

        x, y, w, h = cv2.boundingRect(cnt)

        if (w > ppm * size_mm * (1 - tolerance)) and (h > ppm * size_mm * (1 - tolerance)) and (
                w < ppm * size_mm * (1 + tolerance)) and (
                h < ppm * size_mm * (1 + tolerance)):  # and (y - ppm > 0) and (x - ppm > 0):
            patches.append((x, y, w, h))
        else:
            if (w > ppm * size_mm * 0.2) and (h > ppm * size_mm * 0.2) \
                    and (w < ppm * size_mm * 0.5) and (h < ppm * size_mm * 0.5):
                a = int(ppm * size_mm / 2)
                patches.append((x - a, y - a, w + 2 * a, h + 2 * a))

    return patches


def get_codes(patch):
    codes = set()
    if patch.shape[0] > 0 and patch.shape[1] > 0:
        results = zxingcpp.read_barcodes(patch, formats=zxingcpp.BarcodeFormat.Aztec | zxingcpp.BarcodeFormat.QRCode)
        for result in results:
            if result.text not in codes:
                top_left_x = min(result.position.top_left.x, result.position.bottom_right.x)
                top_left_y = min(result.position.top_left.y, result.position.bottom_right.y)
                width = abs(result.position.top_left.x - result.position.bottom_right.x)
                height = abs(result.position.top_left.y - result.position.bottom_right.y)
                codes.add((result.text, top_left_x, top_left_y, width, height))
    return codes


def get_similarity_transform(p1, p2):
    # p1 and p2: two points each, given as (x, y) tuples
    p1 = np.array(p1, dtype=np.float64)
    p2 = np.array(p2, dtype=np.float64)

    center1 = (p1[0] + p1[1]) / 2
    center2 = (p2[0] + p2[1]) / 2

    v1 = p1[1] - p1[0]
    v2 = p2[1] - p2[0]

    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    scale = norm2 / norm1

    angle1 = np.arctan2(v1[1], v1[0])
    angle2 = np.arctan2(v2[1], v2[0])
    theta = angle2 - angle1

    cos_theta = np.cos(theta)
    sin_theta = np.sin(theta)
    rotation = np.array([[cos_theta, -sin_theta],
                         [sin_theta,  cos_theta]])

    def transform_point(pt):
        pt = np.array(pt, dtype=np.float64)
        vec = pt - center1
        transformed = scale * (rotation @ vec)
        return tuple(transformed + center2)

    return transform_point

def compute_similarity_transform(p11, p12, p21, p22):
    # Convert points to numpy arrays
    p11, p12, p21, p22 = map(np.array, [p11, p12, p21, p22])

    # Compute centroids
    C1 = (p11 + p12) / 2.0
    C2 = (p21 + p22) / 2.0

    # Compute translation vector
    T = C2 - C1

    # Compute scale factor
    d1 = np.linalg.norm(p12 - p11)  # Distance in reference frame A
    d2 = np.linalg.norm(p22 - p21)  # Distance in reference frame B
    s = d2 / d1 if d1 != 0 else 1  # Avoid division by zero

    # Compute rotation angle
    delta1 = p12 - p11
    delta2 = p22 - p21

    theta1 = math.atan2(delta1[1], delta1[0])
    theta2 = math.atan2(delta2[1], delta2[0])
    theta = theta2 - theta1  # Rotation angle in radians

    # Construct rotation matrix
    R = np.array([[math.cos(theta), -math.sin(theta)],
                  [math.sin(theta), math.cos(theta)]])

    # Scale, rotation, and translation
    return s, R, T


def makedir(path, clear=False):
    try:
        os.makedirs(path)
    except FileExistsError:
        if clear:
            directory = Path(path)
            for item in directory.glob('*'):
                if item.is_file() or item.is_symlink():
                    item.unlink()
