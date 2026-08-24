# -*- coding: utf-8 -*-
"""Phat hien chuyen dong bang tach nen MOG2 - dung lam 'cong' truoc khi chay YOLO."""
import cv2
import numpy as np


class MotionDetector(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.bg = cv2.createBackgroundSubtractorMOG2(
            history=int(cfg["motion_history"]),
            varThreshold=float(cfg["motion_var_threshold"]),
            detectShadows=True,
        )
        self.min_ratio = float(cfg["motion_min_area_ratio"])
        self.kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self.warmup = 0
        self.last_mask = None
        self.min_region_side = int(cfg.get('motion_min_region_side', 12))

    def update(self, frame):
        """Tra ve (co_chuyen_dong, mask, ty_le_dien_tich)."""
        small = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        blur = cv2.GaussianBlur(small, (5, 5), 0)
        mask = self.bg.apply(blur)
        mask[mask < 200] = 0            # loai bong (gia tri 127)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.dilate(mask, self.kernel, iterations=2)
        self.last_mask = mask

        self.warmup += 1
        if self.warmup < 12:            # cho MOG2 hoc nen
            return False, mask, 0.0

        ratio = float(np.count_nonzero(mask)) / float(mask.size)
        return ratio >= self.min_ratio, mask, ratio

    def regions(self, frame_shape, min_side=None):
        """Cac o chu nhat bao quanh vung dang chuyen dong (toa do khung hinh goc).

        Sap xep theo dien tich giam dan.
        """
        if self.last_mask is None or self.warmup < 12:
            return []
        if min_side is None:
            min_side = self.min_region_side
        mh, mw = self.last_mask.shape[:2]
        sx = float(frame_shape[1]) / float(mw)
        sy = float(frame_shape[0]) / float(mh)
        cnts, _ = cv2.findContours(self.last_mask, cv2.RETR_EXTERNAL,
                                   cv2.CHAIN_APPROX_SIMPLE)
        out = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w < min_side or h < min_side:
                continue
            out.append((int(x * sx), int(y * sy), int(w * sx), int(h * sy)))
        out.sort(key=lambda b: -(b[2] * b[3]))
        return out

    def motion_ratio_in_box(self, box, frame_shape):
        """Ty le diem anh chuyen dong nam trong khung xe (box theo toa do frame goc)."""
        if self.last_mask is None:
            return 0.0
        x, y, w, h = box
        mh, mw = self.last_mask.shape[:2]
        sx = float(mw) / float(frame_shape[1])
        sy = float(mh) / float(frame_shape[0])
        x1 = max(0, int(x * sx))
        y1 = max(0, int(y * sy))
        x2 = min(mw, int((x + w) * sx))
        y2 = min(mh, int((y + h) * sy))
        if x2 <= x1 or y2 <= y1:
            return 0.0
        sub = self.last_mask[y1:y2, x1:x2]
        return float(np.count_nonzero(sub)) / float(sub.size)
