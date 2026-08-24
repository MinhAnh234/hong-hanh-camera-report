# -*- coding: utf-8 -*-
"""Nhan dang phuong tien bang YOLOv4-tiny (OpenCV DNN, chay CPU).

Camera dat xa nen xe trong khung hinh rat nho. Neu dua ca khung hinh vao mang
thi xe bi thu con vai chuc diem anh va gan nhu khong the nhan ra. Vi vay:

  1. Chi quet nhung O CO CHUYEN DONG (do motion.py cung cap) - vua nhanh vua
     giup xe chiem ty le lon hon trong o duoc quet.
  2. Khi da bat duoc xe, cat sat khung xe va quet lai o do phan giai cao hon
     de PHAN LOAI chinh xac (xe ben / xe tai hay xe con).
"""
import os

import cv2
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models")
CFG_PATH = os.path.join(MODEL_DIR, "yolov4-tiny.cfg")
WEIGHTS_PATH = os.path.join(MODEL_DIR, "yolov4-tiny.weights")
NAMES_PATH = os.path.join(MODEL_DIR, "coco.names")


class Detection(object):
    __slots__ = ("label", "label_vi", "conf", "box")

    def __init__(self, label, label_vi, conf, box):
        self.label = label
        self.label_vi = label_vi
        self.conf = float(conf)
        self.box = tuple(int(v) for v in box)   # (x, y, w, h)

    @property
    def centroid(self):
        x, y, w, h = self.box
        return (x + w / 2.0, y + h / 2.0)

    @property
    def area(self):
        return self.box[2] * self.box[3]


def _overlap_area(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0
    return (x2 - x1) * (y2 - y1)


def _iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1, y1 = max(ax, bx), max(ay, by)
    x2, y2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    return inter / float(aw * ah + bw * bh - inter)


class VehicleDetector(object):
    def __init__(self, cfg):
        for p in (CFG_PATH, WEIGHTS_PATH, NAMES_PATH):
            if not os.path.exists(p):
                raise IOError(u"Thiếu file mô hình: %s" % p)

        with open(NAMES_PATH, "r", encoding="utf-8") as f:
            self.classes = [ln.strip() for ln in f if ln.strip()]

        self.cfg = cfg
        self.conf_th = float(cfg["conf_threshold"])
        self.nms_th = float(cfg["nms_threshold"])
        self.watch = set(cfg["watch_classes"])
        self.names_vi = cfg["classes_vi"]
        self.win_min = int(cfg.get("scan_window_min", 380))
        self.win_pad = float(cfg.get("scan_window_pad", 1.7))
        self.max_regions = int(cfg.get("scan_max_regions", 3))
        self.refine = bool(cfg.get("refine_labels", True))
        self.refine_size = int(cfg.get("refine_input_size", 608))

        net = cv2.dnn.readNetFromDarknet(CFG_PATH, WEIGHTS_PATH)
        net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
        net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
        self._net = net
        self._models = {}
        self._grid_cache = {}
        self.size = int(cfg["input_size"])

    # ---------- ha tang ----------
    def _model(self, size):
        """cv2.dnn_DetectionModel dung chung mang, khac kich thuoc dau vao."""
        if size not in self._models:
            m = cv2.dnn_DetectionModel(self._net)
            m.setInputParams(scale=1 / 255.0, size=(size, size), swapRB=True)
            self._models[size] = m
        return self._models[size]

    def label_vi(self, label):
        return self.names_vi.get(label, label)

    def _raw(self, image, size, conf_th, keep_all=False):
        """Chay mang tren mot anh, tra ve [(label, conf, box)]."""
        if image is None or image.size == 0:
            return []
        try:
            ids, scores, boxes = self._model(size).detect(image, conf_th, self.nms_th)
        except cv2.error:
            return []
        out = []
        if len(ids) == 0:
            return out
        for cid, score, box in zip(np.array(ids).flatten(),
                                   np.array(scores).flatten(),
                                   np.array(boxes).reshape(-1, 4)):
            cid = int(cid)
            if cid < 0 or cid >= len(self.classes):
                continue
            label = self.classes[cid]
            if not keep_all and label not in self.watch:
                continue
            out.append((label, float(score), tuple(int(v) for v in box)))
        return out

    # ---------- quet ca khung hinh ----------
    def detect(self, frame):
        res = self._raw(frame, self.size, self.conf_th)
        return [Detection(l, self.label_vi(l), c, b) for l, c, b in res]

    # ---------- quet theo vung chuyen dong ----------
    def grid(self, frame_shape):
        """Chia khung hinh thanh luoi o chong lan nhau (nho de xe khong bi thu qua nho)."""
        H, W = frame_shape[:2]
        key = (W, H)
        if key in self._grid_cache:
            return self._grid_cache[key]
        cols = max(1, int(round(W / float(self.win_min))))
        rows = max(1, int(round(H / float(self.win_min))))
        ov = 0.25
        tw = int(W / (cols - (cols - 1) * ov)) if cols > 1 else W
        th = int(H / (rows - (rows - 1) * ov)) if rows > 1 else H
        tiles = []
        for i in range(cols):
            for j in range(rows):
                x0 = int(min(W - tw, i * tw * (1 - ov)))
                y0 = int(min(H - th, j * th * (1 - ov)))
                tiles.append((max(0, x0), max(0, y0), tw, th))
        self._grid_cache[key] = tiles
        return tiles

    def _windows(self, frame_shape, regions):
        """Cac o luoi co giao voi vung chuyen dong (uu tien vung dien tich lon)."""
        if not regions:
            return []
        wins = []
        for tile in self.grid(frame_shape):
            hit = max((_overlap_area(tile, r) for r in regions), default=0)
            if hit > 0:
                wins.append((hit, tile))
        wins.sort(key=lambda t: -t[0])
        return [t for _, t in wins[: self.max_regions]]

    def detect_regions(self, frame, regions):
        """Quet cac o luoi co chuyen dong. Tra ve danh sach Detection."""
        if not regions:
            return []
        found = []
        for (x0, y0, ww, hh) in self._windows(frame.shape, regions):
            crop = frame[y0:y0 + hh, x0:x0 + ww]
            for label, conf, (bx, by, bw, bh) in self._raw(crop, self.size, self.conf_th):
                found.append((label, conf, (bx + x0, by + y0, bw, bh)))

        # gop trung lap giua cac o
        found.sort(key=lambda t: -t[1])
        kept = []
        for label, conf, box in found:
            if any(_iou(box, k[2]) > 0.45 for k in kept):
                continue
            kept.append((label, conf, box))

        dets = []
        for label, conf, box in kept:
            if self.refine:
                label, conf = self.refine_label(frame, box, label, conf)
            dets.append(Detection(label, self.label_vi(label), conf, box))
        return dets

    def refine_label(self, frame, box, label, conf):
        """Cat sat khung xe, quet lai o do phan giai cao de phan loai chinh xac hon."""
        H, W = frame.shape[:2]
        x, y, w, h = box
        cx, cy = x + w / 2.0, y + h / 2.0
        side = max(w, h) * 2.2
        side = max(side, 160)
        side = min(side, min(W, H))
        x0 = int(max(0, min(W - side, cx - side / 2.0)))
        y0 = int(max(0, min(H - side, cy - side / 2.0)))
        crop = frame[y0:y0 + int(side), x0:x0 + int(side)]
        best = None
        for lb, cf, (bx, by, bw, bh) in self._raw(crop, self.refine_size, self.conf_th * 0.8):
            if lb not in self.watch:
                continue
            if _iou((bx + x0, by + y0, bw, bh), box) < 0.25:
                continue
            if best is None or cf > best[1]:
                best = (lb, cf)
        if best is None:
            return label, conf
        return best[0], max(conf, best[1])
