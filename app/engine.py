# -*- coding: utf-8 -*-
"""Bo may giam sat: chup man hinh -> phat hien chuyen dong -> nhan dang xe -> luu su kien."""
import threading
import time

from .capture import WindowCapture, enable_dpi_awareness
from .detector import VehicleDetector
from .motion import MotionDetector
from .storage import Session
from .tracker import VehicleTracker


class MonitorEngine(object):
    """Chay trong luong rieng. Gui trang thai ra ngoai qua cac callback."""

    def __init__(self, cfg, on_event=None, on_status=None, on_frame=None):
        self.cfg = cfg
        self.on_event = on_event or (lambda ev, tr: None)
        self.on_status = on_status or (lambda st: None)
        self.on_frame = on_frame or (lambda frame, dets: None)

        self.session = None
        self._thread = None
        self._stop = threading.Event()
        self.running = False

        self.stats = {
            "khung_hinh": 0,
            "khung_bo_qua": 0,
            "lan_chuyen_dong": 0,
            "lan_nhan_dang": 0,
            "su_kien": 0,
            "loi": "",
        }
        self._last_event_ts = {}

    # ---- dieu khien ----
    def start(self):
        if self.running:
            return self.session
        enable_dpi_awareness()
        self.session = Session(self.cfg)
        self._stop.clear()
        self.running = True
        self._thread = threading.Thread(target=self._loop, name="giam-sat", daemon=True)
        self._thread.start()
        return self.session

    def stop(self, timeout=6.0):
        if not self.running:
            return
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout)
        self.running = False
        if self.session is not None:
            self.session.close()

    # ---- vong lap chinh ----
    def _loop(self):
        cfg = self.cfg
        cap = WindowCapture(cfg)
        motion = MotionDetector(cfg)
        tracker = VehicleTracker(cfg)

        try:
            detector = VehicleDetector(cfg)
        except Exception as e:
            self.stats["loi"] = u"Không nạp được mô hình nhận dạng: %s" % e
            self.on_status(dict(self.stats, trang_thai=u"LỖI"))
            self.running = False
            return

        if not cap.attach():
            self.stats["loi"] = cap.last_error
            self.on_status(dict(self.stats, trang_thai=u"CHỜ CỬA SỔ IMOU"))

        interval = 1.0 / max(float(cfg.get("fps", 5.0)), 0.5)
        cooldown = float(cfg.get("event_cooldown_sec", 4.0))
        min_motion_in_box = float(cfg.get("min_motion_in_box", 0.01))
        last_status = 0.0
        state = u"ĐANG GIÁM SÁT"

        while not self._stop.is_set():
            tick = time.time()
            frame, err = cap.grab()

            if frame is None:
                self.stats["khung_bo_qua"] += 1
                self.stats["loi"] = err
                state = u"TẠM DỪNG"
                cap.attach()
            else:
                self.stats["khung_hinh"] += 1
                self.stats["loi"] = ""
                state = u"ĐANG GIÁM SÁT"

                motion.update(frame)
                regions = motion.regions(frame.shape)
                dets = []
                if regions:
                    self.stats["lan_chuyen_dong"] += 1
                    dets = detector.detect_regions(frame, regions)
                    # chi giu xe that su dang chuyen dong (trung vung mask)
                    if min_motion_in_box > 0:
                        dets = [
                            d for d in dets
                            if motion.motion_ratio_in_box(d.box, frame.shape) >= min_motion_in_box
                        ]
                    if dets:
                        self.stats["lan_nhan_dang"] += 1

                now = time.time()
                for tr in tracker.update(dets, frame, now):
                    prev = self._last_event_ts.get(tr.label, 0.0)
                    if now - prev < cooldown:
                        continue
                    self._last_event_ts[tr.label] = now
                    try:
                        ev = self.session.add_event(tr)
                    except Exception as e:
                        self.stats["loi"] = u"Lỗi lưu ảnh: %s" % e
                        continue
                    self.stats["su_kien"] += 1
                    self.on_event(ev, tr)

                self.on_frame(frame, dets)

            if time.time() - last_status > 0.5:
                last_status = time.time()
                self.on_status(dict(self.stats, trang_thai=state))

            wait = interval - (time.time() - tick)
            if wait > 0:
                self._stop.wait(wait)

        cap.close()
        self.on_status(dict(self.stats, trang_thai=u"ĐÃ DỪNG"))
