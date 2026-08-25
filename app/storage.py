# -*- coding: utf-8 -*-
"""Quan ly phien lam viec: thu muc anh, ghi su kien ra JSON."""
import json
import os
from datetime import datetime

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAPTURE_DIR = os.path.join(ROOT, "captures")
REPORT_DIR = os.path.join(ROOT, "reports")

_FONT_FILES = (
    r"C:\Windows\Fonts\segoeui.ttf",
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\tahoma.ttf",
)
_FONT_CACHE = {}


def _font(size):
    """Font co dau tieng Viet; neu khong co thi dung font mac dinh cua Pillow."""
    if size not in _FONT_CACHE:
        f = None
        for path in _FONT_FILES:
            if os.path.exists(path):
                try:
                    f = ImageFont.truetype(path, size)
                    break
                except Exception:
                    pass
        _FONT_CACHE[size] = f or ImageFont.load_default()
    return _FONT_CACHE[size]


BOX_COLOR = {
    "truck": (0, 165, 255),
    "bus": (0, 200, 255),
    "car": (60, 220, 60),
}


def _imwrite(path, img):
    """Ghi anh, chiu duoc duong dan co dau tieng Viet."""
    ext = os.path.splitext(path)[1] or ".jpg"
    ok, buf = cv2.imencode(ext, img, [int(cv2.IMWRITE_JPEG_QUALITY), 92])
    if not ok:
        return False
    with open(path, "wb") as f:
        f.write(buf.tobytes())
    return True


class Session(object):
    def __init__(self, cfg, session_id=None):
        self.cfg = cfg
        started = datetime.now()
        self.session_id = session_id or ("PHIEN-" + started.strftime("%Y%m%d-%H%M%S"))
        self.started_at = started
        self.dir = os.path.join(CAPTURE_DIR, self.session_id)
        os.makedirs(self.dir, exist_ok=True)
        os.makedirs(REPORT_DIR, exist_ok=True)
        self.events_path = os.path.join(self.dir, "events.json")
        self.events = []
        self.seq = 0
        self._write_meta()

    # ---- ghi du lieu ----
    def _write_meta(self):
        self.meta = {
            "ma_phien": self.session_id,
            "camera": self.cfg.get("camera_name", ""),
            "bat_dau": self.started_at.strftime("%Y-%m-%d %H:%M:%S"),
            "ket_thuc": None,
            "nguon": u"Chụp màn hình cửa sổ Imou",
        }
        self._flush()

    def _flush(self):
        data = {"phien": self.meta, "su_kien": self.events}
        tmp = self.events_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.events_path)

    def close(self):
        self.meta["ket_thuc"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._flush()

    # ---- luu su kien ----
    def add_event(self, track, note=""):
        self.seq += 1
        ts = datetime.fromtimestamp(track.first_ts)
        code = "%s-%03d" % (self.session_id, self.seq)
        stamp = ts.strftime("%Y%m%d-%H%M%S")
        base = "%03d_%s_%s" % (self.seq, track.label, stamp)

        label_vi = track.label_vi(self.cfg.get("classes_vi", {}))
        frame = track.best_frame
        raw_name = base + ".jpg"
        _imwrite(os.path.join(self.dir, raw_name), frame)

        ann_name = ""
        if self.cfg.get("save_annotated", True):
            ann = self._annotate(frame, track, code, ts, label_vi)
            ann_name = base + "_danhdau.jpg"
            _imwrite(os.path.join(self.dir, ann_name), ann)

        h, w = frame.shape[:2]
        ev = {
            "ma_luot": code,
            "stt": self.seq,
            "thoi_gian": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "gio": ts.hour,
            "loai_xe": track.label,
            "loai_xe_vi": label_vi,
            "do_tin_cay": round(float(track.best_conf), 3),
            "khung": list(track.best_det.box),
            "quang_duong_px": round(float(track.path_len), 1),
            "so_khung_hinh": track.hits,
            "kich_thuoc_anh": [int(w), int(h)],
            "anh": raw_name,
            "anh_danh_dau": ann_name,
            "ghi_chu": note,
        }
        self.events.append(ev)
        self._flush()
        return ev

    # ---- su kien lay tu camera (Imou tu phat hien) ----
    def add_camera_event(self, thoi_gian, image, loai_xe="vehicle",
                         loai_xe_vi=u"Phương tiện", note=u"", chac_chan=True,
                         khung=None, do_tin_cay=None, huong=None, dx=None):
        """Luu mot su kien do CHINH CAMERA phat hien (anh + moc thoi gian)."""
        self.seq += 1
        ts = datetime.strptime(thoi_gian, "%Y-%m-%d %H:%M:%S")
        code = "%s-%03d" % (self.session_id, self.seq)
        base = "%03d_%s_%s" % (self.seq, loai_xe, ts.strftime("%Y%m%d-%H%M%S"))

        img = image
        if img.shape[1] < 480:          # anh trong danh sach rat nho -> phong to cho de nhin
            k = 480.0 / img.shape[1]
            img = cv2.resize(img, None, fx=k, fy=k, interpolation=cv2.INTER_LANCZOS4)
        raw_name = base + ".jpg"
        _imwrite(os.path.join(self.dir, raw_name), img)

        ann_name = ""
        if self.cfg.get("save_annotated", True):
            ann_name = base + "_danhdau.jpg"
            _imwrite(os.path.join(self.dir, ann_name),
                     self._banner(img, code, ts, loai_xe_vi, khung, loai_xe))

        h, w = img.shape[:2]
        ev = {
            "ma_luot": code,
            "stt": self.seq,
            "thoi_gian": ts.strftime("%Y-%m-%d %H:%M:%S"),
            "gio": ts.hour,
            "loai_xe": loai_xe,
            "loai_xe_vi": loai_xe_vi,
            "do_tin_cay": do_tin_cay,
            "khung": list(khung) if khung else None,
            "huong": huong,
            "dx": dx,
            "quang_duong_px": None,
            "so_khung_hinh": None,
            "kich_thuoc_anh": [int(w), int(h)],
            "anh": raw_name,
            "anh_danh_dau": ann_name,
            "nguon_su_kien": u"Camera tự phát hiện",
            "thoi_gian_chac_chan": bool(chac_chan),
            "ghi_chu": note or (u"" if chac_chan
                                else u"Mốc giờ đọc tự động – nên đối chiếu lại"),
        }
        self.events.append(ev)
        self._flush()
        return ev

    def _banner(self, img, code, ts, nhan, khung=None, loai_xe=None):
        """Dan dai thong tin duoi anh; ve them khung xe neu co."""
        out = img.copy()
        ih, iw = out.shape[:2]
        if khung:
            x, y, w, h = [int(v) for v in khung]
            cv2.rectangle(out, (x, y), (x + w, y + h),
                          BOX_COLOR.get(loai_xe, (0, 165, 255)), 3)
        overlay = out.copy()
        cv2.rectangle(overlay, (0, ih - 34), (iw, ih), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.58, out, 0.42, 0, out)
        pil = Image.fromarray(cv2.cvtColor(out, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil)
        draw.text((10, ih - 27),
                  u"%s  |  %s  |  %s" % (code, ts.strftime("%d-%m-%Y %H:%M:%S"), nhan),
                  font=_font(15), fill=(255, 255, 255))
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

    def _annotate(self, frame, track, code, ts, label_vi):
        """Ve khung xe + dai thong tin. Dung Pillow de viet duoc tieng Viet co dau."""
        img = frame.copy()
        x, y, w, h = track.best_det.box
        color = BOX_COLOR.get(track.label, (0, 200, 255))
        cv2.rectangle(img, (x, y), (x + w, y + h), color, 3)

        ih, iw = img.shape[:2]
        overlay = img.copy()
        cv2.rectangle(overlay, (0, ih - 38), (iw, ih), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.55, img, 0.45, 0, img)

        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(pil)
        tag = u"%s %.0f%%" % (label_vi, track.best_conf * 100)
        f_tag, f_banner = _font(20), _font(17)

        tw = int(draw.textlength(tag, font=f_tag))
        ty = max(28, y)
        draw.rectangle([x, ty - 26, x + tw + 12, ty], fill=(color[2], color[1], color[0]))
        draw.text((x + 6, ty - 24), tag, font=f_tag, fill=(25, 25, 25))

        banner = u"%s  |  %s  |  %s" % (
            code, ts.strftime("%d-%m-%Y %H:%M:%S"), self.cfg.get("camera_name", ""))
        draw.text((12, ih - 30), banner, font=f_banner, fill=(255, 255, 255))
        return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


def load_session(session_id):
    path = os.path.join(CAPTURE_DIR, session_id, "events.json")
    if not os.path.exists(path):
        raise IOError(u"Không tìm thấy phiên: %s" % session_id)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_sessions():
    if not os.path.isdir(CAPTURE_DIR):
        return []
    out = []
    for name in sorted(os.listdir(CAPTURE_DIR), reverse=True):
        if os.path.exists(os.path.join(CAPTURE_DIR, name, "events.json")):
            out.append(name)
    return out
