# -*- coding: utf-8 -*-
"""Chup ANH NET cho tung su kien phuong tien.

Anh trong danh sach su kien cua Imou chi la thumbnail 110x60 nen rat mo. Nhung
moi su kien deu co mot CLIP GHI HINH tuong ung trong "Xem Lai > Ban ghi noi bo".
Module nay mo dung clip do, cho no chay, chup lai khung hinh o do phan giai that
(hon 1500 diem anh chieu ngang) va chon khung hinh co xe ro nhat.
"""
import ctypes
import re
import time
from datetime import datetime

import cv2
import numpy as np
import win32api
import win32con
import win32gui

from . import ocr
from .capture import detect_video_rect, list_windows, print_window
from .imou_events import ImouUI

PLAYER_TITLE = "SinglePlayerDlg"
_GIO = re.compile(r"^(\d{2})(\d{2})(\d{2})$")


# ---------------------------------------------------------------- danh sach clip
def _runs(mask1d, lo, hi, offset=0):
    """Cac doan lien tuc co do dai trong khoang [lo, hi]."""
    out, s = [], None
    for i, v in enumerate(mask1d):
        if v and s is None:
            s = i
        elif not v and s is not None:
            if lo <= i - s <= hi:
                out.append((s + offset, i - 1 + offset))
            s = None
    if s is not None and lo <= len(mask1d) - s <= hi:
        out.append((s + offset, len(mask1d) - 1 + offset))
    return out


def find_clip_cards(img, x0=265, y0=220):
    """Tim cac the clip theo luoi -> [(x1, y1, x2, y2)]."""
    h, w = img.shape[:2]
    nen = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) > 238      # nen trang cua trang
    cot_mau = ~nen[:, min(w - 1, x0 + 141)]
    hang = _runs(cot_mau[y0:h - 40], 90, 200, y0)

    cards = []
    for ya, yb in hang:
        y = (ya + yb) // 2
        for xa, xb in _runs(~nen[y, x0:w - 10], 180, 320, x0):
            cards.append((xa, ya, xb, yb))
    return cards


def read_clip_time(img, card):
    """Doc gio bat dau cua clip (chu trang goc duoi trai thumbnail) -> 'HH:MM:SS'."""
    xa, _ya, _xb, yb = card
    crop = img[yb - 27:yb - 3, xa + 3:xa + 120]
    if crop.size == 0:
        return None
    for nguong in (175, 150, 200):
        g = cv2.resize(cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY), None,
                       fx=6, fy=6, interpolation=cv2.INTER_CUBIC)
        _, bw = cv2.threshold(g, nguong, 255, cv2.THRESH_BINARY)
        text = ocr.read_text(cv2.cvtColor(255 - bw, cv2.COLOR_GRAY2BGR)).replace("\n", " ")
        so = "".join(c for c in text if c.isdigit())
        m = _GIO.match(so)
        if m and int(m.group(1)) <= 23 and int(m.group(2)) <= 59 and int(m.group(3)) <= 59:
            return "%s:%s:%s" % m.groups()
    return None


# ---------------------------------------------------------------- cua so phat clip
def _player_hwnd():
    wins = list_windows(PLAYER_TITLE)
    return wins[0] if wins else None


def _close_player():
    h = _player_hwnd()
    if h:
        try:
            win32gui.PostMessage(h, win32con.WM_CLOSE, 0, 0)
        except Exception:
            pass
        time.sleep(1.0)


def _phong_to_player(hwnd, rong=1600, cao=980):
    """Phong to cua so phat clip de khung hinh chup duoc net hon."""
    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        if (r - l) >= rong - 40:
            return False
        man_w = win32api.GetSystemMetrics(0)
        man_h = win32api.GetSystemMetrics(1)
        rong = min(rong, man_w - 40)
        cao = min(cao, man_h - 60)
        win32gui.MoveWindow(hwnd, max(0, (man_w - rong) // 2),
                            max(0, (man_h - cao) // 2), rong, cao, True)
        return True
    except Exception:
        return False


def _cho_player(timeout=12.0):
    het = time.time() + timeout
    while time.time() < het:
        h = _player_hwnd()
        if h:
            img = print_window(h)
            if img is not None and img.std() > 8:
                ImouUI.dua_len_tren(h, True)
                if _phong_to_player(h):
                    time.sleep(3.0)          # cho video tai lai sau khi doi kich thuoc
                return h
        time.sleep(0.5)
    return None


def _phat_lai(hwnd):
    """Bam nut 'phat lai' o giua khung hinh khi clip da chay het."""
    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
        x, y = l + (r - l) // 2, t + int((b - t) * 0.48)
        user32 = ctypes.windll.user32
        user32.SetCursorPos(x, y)
        time.sleep(0.3)
        user32.mouse_event(0x0002, 0, 0, 0, 0)
        time.sleep(0.08)
        user32.mouse_event(0x0004, 0, 0, 0, 0)
        time.sleep(0.3)
        user32.SetCursorPos(x, b - 8)
        time.sleep(1.2)
    except Exception:
        pass


def _co_hinh(khung, nguong=12.0):
    """Khung hinh co phai video that khong (man hinh cho / dang tai thi rat phang)."""
    return khung is not None and khung.size > 0 and float(khung.std()) >= nguong


def chup_tu_player(hwnd, detector, so_khung=10, moi_khung=0.7, cho_toi_da=14.0):
    """Chup nhieu khung hinh trong luc clip chay, chon khung co xe ro nhat.

    Tra ve (anh_BGR, detection_tot_nhat | None). Bo qua nhung khung hinh trong
    (man hinh cho mau xam) de khong luu nham anh khong co gi.
    """
    img = print_window(hwnd)
    if img is None:
        return None, None
    roi = detect_video_rect(img) or {"left": 0.0, "top": 0.09, "right": 1.0, "bottom": 0.93}

    def cat(anh):
        # Cat bo 2 nut mui ten chuyen clip nam sat mep trai/phai cua khung hinh
        h, w = anh.shape[:2]
        x1 = int(w * roi["left"]) + 24
        x2 = int(w * roi["right"]) - 24
        y1, y2 = int(h * roi["top"]), int(h * roi["bottom"])
        return anh[max(0, y1):y2, max(0, x1):x2]

    # --- doi den khi video that su hien ra ---
    het = time.time() + cho_toi_da
    da_bam_lai = False
    while time.time() < het:
        anh = print_window(hwnd)
        if anh is not None and _co_hinh(cat(anh)):
            break
        if not da_bam_lai and time.time() > het - cho_toi_da / 2:
            _phat_lai(hwnd)              # co the clip da chay het truoc khi ta kip chup
            da_bam_lai = True
        time.sleep(0.6)

    tot_anh, tot_det, tot_diem = None, None, -1.0
    du_phong, truoc, dung_yen = None, None, 0
    for i in range(so_khung):
        anh = print_window(hwnd)
        if anh is not None:
            if truoc is not None and anh.shape == truoc.shape:
                if float(np.abs(anh.astype(int) - truoc.astype(int)).mean()) < 0.05:
                    dung_yen += 1
                    if dung_yen == 3:        # clip da chay het -> phat lai
                        _phat_lai(hwnd)
                        dung_yen = 0
                else:
                    dung_yen = 0
            truoc = anh

            khung = cat(anh)
            if _co_hinh(khung):
                if du_phong is None or i == so_khung // 2:
                    du_phong = khung.copy()
                if detector is not None:
                    ca = [(0, 0, khung.shape[1], khung.shape[0])]
                    for d in detector.detect_regions(khung, ca):
                        diem = d.conf * (1.0 + d.area / 1e6)
                        if diem > tot_diem:
                            tot_diem, tot_det, tot_anh = diem, d, khung.copy()
        time.sleep(moi_khung)
    return (tot_anh if tot_anh is not None else du_phong), tot_det


# ---------------------------------------------------------------- luong chinh
def _giay(hms):
    h, m, s = [int(v) for v in hms.split(":")]
    return h * 3600 + m * 60 + s


def chup_anh_net(cfg, events, log=print, lech_toi_da=240):
    """Voi moi su kien, mo clip gan nhat va chup mot khung hinh net.

    events: [{'thoi_gian': 'YYYY-MM-DD HH:MM:SS', ...}] - se duoc them khoa 'anh_net'.
    Tra ve so su kien da chup duoc.
    """
    from .detector import VehicleDetector

    try:
        detector = VehicleDetector(cfg)
    except Exception as e:
        log(u"  (!) Không nạp được mô hình nhận dạng: %s" % e)
        detector = None

    ui = ImouUI(cfg)
    if not ui.attach():
        raise RuntimeError(ui.cap.last_error or u"Không tìm thấy cửa sổ Imou.")
    _close_player()

    ngay = datetime.strptime(events[0]["thoi_gian"], "%Y-%m-%d %H:%M:%S").date()

    log(u"• Mở tab Xem Lại…")
    tab = ocr.find_line(ocr.read(ui.shot()[0:90, 0:400], scale=2.0), u"xem", u"lai")
    if tab is None:
        raise RuntimeError(u"Không tìm thấy tab 'Xem Lại'.")
    ui.click(tab.center[0], tab.center[1], settle=2.5)

    log(u"• Chọn camera %s…" % cfg.get("camera_name", ""))
    if not ui.select_device(cfg.get("camera_name", "")):
        raise RuntimeError(u"Không tìm thấy camera trong danh sách.")

    log(u"• Chọn ngày %s…" % ngay.strftime("%d-%m-%Y"))
    ui.select_day(ngay.day)
    time.sleep(1.5)

    con_lai = sorted(events, key=lambda e: e["thoi_gian"], reverse=True)   # moi -> cu
    xong = 0

    for lan in range(2):                 # quet 2 luot: luot 2 vot not su kien con sot
        if not con_lai:
            break
        if lan:
            log(u"• Quét lại lượt 2 cho %d sự kiện còn thiếu…" % len(con_lai))
        ui.scroll(-30)                   # ve dau danh sach
        time.sleep(1.0)

        for _vong in range(60):
            if not con_lai:
                break
            img = ui.shot()
            the = [(c, read_clip_time(img, c)) for c in find_clip_cards(img)]
            the = [(c, t) for c, t in the if t]

            lam_gi = None
            for ev in list(con_lai):
                muc = _giay(ev["thoi_gian"][11:])
                gan = None
                for c, t in the:
                    d = abs(_giay(t) - muc)
                    if d <= lech_toi_da and (gan is None or d < gan[1]):
                        gan = (c, d, t)
                if gan:
                    lam_gi = (ev, gan)
                    break

            if lam_gi is None:
                ui.scroll(4)
                continue

            ev, (card, lech, gio_clip) = lam_gi
            xa, ya, xb, yb = card
            log(u"  → %s  ← clip %s (lệch %ds)" % (ev["thoi_gian"][11:], gio_clip, lech))
            ui.click((xa + xb) // 2, (ya + yb) // 2, double=True, settle=2.0)

            h = _cho_player()
            if h is None:
                log(u"     (!) Không mở được clip, bỏ qua.")
                con_lai.remove(ev)
                continue
            anh, det = chup_tu_player(h, detector)
            _close_player()

            if anh is not None:
                ev["anh_net"] = anh
                ev["khung_xe"] = det.box if det is not None else None
                ev["tin_cay"] = round(float(det.conf), 3) if det is not None else None
                ev["loai_xe_net"] = det.label if det is not None else None
                xong += 1
                log(u"     ✔ ảnh %dx%d%s" % (
                    anh.shape[1], anh.shape[0],
                    u" – nhận ra %s %.0f%%" % (det.label, det.conf * 100) if det else u""))
            else:
                log(u"     (!) Không chụp được khung hình.")
            con_lai.remove(ev)

    ui.tra_lai()                      # bo co "luon noi tren cung"
    if con_lai:
        log(u"  (!) Còn %d sự kiện không tìm thấy clip tương ứng." % len(con_lai))
    return xong
