# -*- coding: utf-8 -*-
"""Bam vet xe giua cac khung hinh de moi luot xe chi sinh 1 su kien.

Luu y: mo hinh co the doi nhan giua cac khung hinh (luc "car" luc "truck") voi
cung mot chiec xe o xa. Vi vay vet duoc ghep theo VI TRI, con nhan cuoi cung do
cac lan nhin thay BO PHIEU (trong so = do tin cay).
"""
import math
from collections import defaultdict


def iou(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    x1 = max(ax, bx)
    y1 = max(ay, by)
    x2 = min(ax + aw, bx + bw)
    y2 = min(ay + ah, by + bh)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    inter = (x2 - x1) * (y2 - y1)
    return inter / float(aw * ah + bw * bh - inter)


def _center_dist(a, b):
    ax = a[0] + a[2] / 2.0
    ay = a[1] + a[3] / 2.0
    bx = b[0] + b[2] / 2.0
    by = b[1] + b[3] / 2.0
    return math.hypot(ax - bx, ay - by)


class Track(object):
    _next_id = 1

    def __init__(self, det, frame, ts):
        self.id = Track._next_id
        Track._next_id += 1
        self.votes = defaultdict(float)
        self.box = det.box
        self.start_pt = det.centroid
        self.last_pt = det.centroid
        self.hits = 0
        self.missing = 0
        self.path_len = 0.0
        self.first_ts = ts
        self.last_ts = ts
        self.best_conf = 0.0
        self.best_det = det
        self.best_frame = None
        self.reported = False
        self._absorb(det, frame, ts, moved=0.0)

    # ---- cap nhat ----
    def _absorb(self, det, frame, ts, moved):
        self.votes[det.label] += det.conf
        self.path_len += moved
        self.last_pt = det.centroid
        self.box = det.box
        self.hits += 1
        self.missing = 0
        self.last_ts = ts
        score = det.conf * (1.0 + det.area / 1e6)
        best = self.best_det.conf * (1.0 + self.best_det.area / 1e6)
        if self.best_frame is None or score >= best:
            self.best_det = det
            self.best_frame = frame.copy()
        self.best_conf = max(self.best_conf, det.conf)

    def update(self, det, frame, ts):
        px, py = self.last_pt
        cx, cy = det.centroid
        self._absorb(det, frame, ts, math.hypot(cx - px, cy - py))

    # ---- ket qua ----
    @property
    def label(self):
        return max(self.votes.items(), key=lambda kv: kv[1])[0]

    @property
    def displacement(self):
        return math.hypot(self.last_pt[0] - self.start_pt[0],
                          self.last_pt[1] - self.start_pt[1])

    def label_vi(self, names_vi):
        return names_vi.get(self.label, self.label)


class VehicleTracker(object):
    """Ghep detection voi vet cu; xac nhan vet khi xe da di chuyen du xa."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.tracks = []
        self.min_hits = int(cfg["track_min_hits"])
        self.min_move = float(cfg["track_min_move_px"])
        self.max_missing = int(cfg["track_max_missing"])
        self.names_vi = cfg.get("classes_vi", {})

    def update(self, detections, frame, ts):
        """Tra ve danh sach Track vua duoc xac nhan (can luu su kien)."""
        used = set()
        for tr in self.tracks:
            best_i, best_score = -1, 0.0
            for i, det in enumerate(detections):
                if i in used:
                    continue
                score = iou(tr.box, det.box)
                if score < 0.15:
                    # xe nho o xa co the truot han khung -> chap nhan theo khoang cach
                    ref = max(tr.box[2], tr.box[3], det.box[2], det.box[3])
                    if _center_dist(tr.box, det.box) < ref * 1.6:
                        score = 0.16
                if score > best_score:
                    best_score, best_i = score, i
            if best_i >= 0 and best_score >= 0.15:
                used.add(best_i)
                tr.update(detections[best_i], frame, ts)
            else:
                tr.missing += 1

        for i, det in enumerate(detections):
            if i not in used:
                self.tracks.append(Track(det, frame, ts))

        confirmed = []
        for tr in self.tracks:
            if tr.reported or tr.hits < self.min_hits:
                continue
            if tr.displacement >= self.min_move or tr.path_len >= self.min_move * 1.5:
                tr.reported = True
                confirmed.append(tr)

        self.tracks = [t for t in self.tracks if t.missing <= self.max_missing]
        return confirmed

    def active_count(self):
        return len([t for t in self.tracks if t.missing == 0])
