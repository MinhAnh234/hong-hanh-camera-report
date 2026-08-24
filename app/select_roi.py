# -*- coding: utf-8 -*-
"""Chon vung chup (ROI) tren cua so Imou.

Chay:  python -m app.select_roi          -> tu do vung video, cho xem truoc
       python -m app.select_roi --tay    -> tu keo chuot chon vung
"""
import sys

import cv2

from . import config
from .capture import WindowCapture, detect_video_rect, enable_dpi_awareness


def _fit(img, max_w=1280):
    scale = min(1.0, float(max_w) / img.shape[1])
    if scale >= 1.0:
        return img, 1.0
    return cv2.resize(img, (int(img.shape[1] * scale), int(img.shape[0] * scale))), scale


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    thu_cong = "--tay" in argv

    enable_dpi_awareness()
    cfg = config.load()
    cap = WindowCapture(cfg)
    if not cap.attach():
        print(cap.last_error)
        return 1

    img, err = cap.grab_full()
    if img is None:
        print(err)
        return 1
    h, w = img.shape[:2]
    print(u"Cửa sổ: %dx%d | chế độ chụp: %s" % (w, h, cap.mode))

    roi = None
    if not thu_cong:
        roi = detect_video_rect(img)
        if roi is None:
            print(u"Không tự dò được vùng video – chuyển sang chọn tay.")
        else:
            view, scale = _fit(img.copy())
            p1 = (int(roi["left"] * w * scale), int(roi["top"] * h * scale))
            p2 = (int(roi["right"] * w * scale), int(roi["bottom"] * h * scale))
            cv2.rectangle(view, p1, p2, (0, 165, 255), 2)
            title = "Vung tu do - ENTER: dong y | R: chon lai bang chuot | ESC: huy"
            cv2.imshow(title, view)
            key = cv2.waitKey(0) & 0xFF
            cv2.destroyAllWindows()
            if key == 27:
                print(u"Đã huỷ – giữ nguyên vùng chụp cũ.")
                return 0
            if key in (ord("r"), ord("R")):
                roi = None

    if roi is None:
        view, scale = _fit(img)
        title = "Keo chuot chon vung khung hinh video - ENTER de luu, C de huy"
        box = cv2.selectROI(title, view, showCrosshair=False, fromCenter=False)
        cv2.destroyAllWindows()
        if box is None or box[2] < 20 or box[3] < 20:
            print(u"Đã huỷ – giữ nguyên vùng chụp cũ.")
            return 0
        x, y, bw, bh = [v / scale for v in box]
        roi = {
            "left": round(max(0.0, x / w), 4),
            "top": round(max(0.0, y / h), 4),
            "right": round(min(1.0, (x + bw) / w), 4),
            "bottom": round(min(1.0, (y + bh) / h), 4),
        }

    cfg["roi"] = roi
    path = config.save(cfg)
    print(u"Đã lưu vùng chụp vào %s" % path)
    print(u"  %s" % roi)
    return 0


if __name__ == "__main__":
    sys.exit(main())
