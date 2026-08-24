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
TEN_HUONG = {"trai_sang_phai": u"trái → phải (ra khỏi mỏ)",
             "phai_sang_trai": u"phải → trái (vào mỏ)"}
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


def chup_tu_player(hwnd, detector, cfg=None, so_khung=16, moi_khung=0.8,
                   cho_toi_da=14.0):
    """Chup nhieu khung hinh trong luc clip chay, chon khung co xe ro nhat.

    Dong thoi BAM VET xe qua cac khung hinh de biet no di TU TRAI QUA PHAI hay
    nguoc lai (xe ra khoi mo hay vao mo).

    Tra ve (anh_BGR, detection_tot_nhat | None, huong | None, dx).
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

    bam = None
    if detector is not None and cfg is not None:
        from .tracker import VehicleTracker
        bam = VehicleTracker(cfg)

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
                    dets = detector.detect_regions(khung, ca)
                    if bam is not None:
                        bam.update(dets, khung, i * moi_khung)
                    for d in dets:
                        diem = d.conf * (1.0 + d.area / 1e6)
                        if diem > tot_diem:
                            tot_diem, tot_det, tot_anh = diem, d, khung.copy()
        time.sleep(moi_khung)

    huong, dx = None, 0.0
    if bam is not None:
        vets = [t for t in bam.tracks if t.hits >= 2]
        if vets:
            v = max(vets, key=lambda t: abs(t.dx))     # vet di xa nhat theo chieu ngang
            dx = v.dx
            huong = v.huong(float(cfg.get("huong_min_dx", 25)))
    return (tot_anh if tot_anh is not None else du_phong), tot_det, huong, dx


# ---------------------------------------------------------------- luong chinh
def _giay(hms):
    h, m, s = [int(v) for v in hms.split(":")]
    return h * 3600 + m * 60 + s


def chon_tab_ban_ghi(ui, log=None):
    """Bam vao tab 'Ban ghi noi bo' (app vua mo thuong dang o 'Ban ghi dam may')."""
    noi = log or (lambda *_a: None)
    img = ui.shot()
    lines = ocr.read(img[160:235, 265:950], scale=2.2)
    hit = ocr.find_line(lines, u"noi", u"bo")
    if hit is None:
        noi(u"  (!) Không thấy tab 'Bản ghi nội bộ' – dùng tab đang mở.")
        return False
    cx, cy = hit.center
    ui.click(cx + 265, cy + 160, settle=2.5)
    return True


def cho_the_clip(ui, timeout=20.0):
    """Cho danh sach clip hien ra sau khi doi tab / doi ngay."""
    het = time.time() + timeout
    while time.time() < het:
        img = ui.shot()
        if [c for c in find_clip_cards(img) if read_clip_time(img, c)]:
            return True
        time.sleep(1.5)
    return False


def chup_anh_net(cfg, events, log=print, lech_toi_da=120):
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

    log(u"• Chọn tab Bản ghi nội bộ…")
    chon_tab_ban_ghi(ui, log)

    log(u"• Chọn ngày %s…" % ngay.strftime("%d-%m-%Y"))
    if not ui.select_day(ngay.day):
        ui.tra_lai()
        raise RuntimeError(
            u"Không chọn được ngày %d ở tab Xem Lại (đang mở ngày %s). "
            u"Bỏ qua bước chụp ảnh nét để tránh lấy clip của ngày khác."
            % (ngay.day, ui.ngay_dang_chon()))
    time.sleep(1.5)
    if not cho_the_clip(ui):
        log(u"  (!) Danh sách clip chưa hiện ra sau 20 giây.")

    # ---- Buoc 1: quet TOAN BO danh sach clip cua ngay de biet co nhung clip nao ----
    log(u"• Quét toàn bộ danh sách clip trong ngày…")
    gio_clip = quet_danh_sach_clip(ui, log)
    log(u"  thấy %d clip." % len(gio_clip))

    # ---- Buoc 2: ghep moi su kien voi clip gan nhat ----
    can_mo = {}                       # gio_clip -> danh sach su kien
    khong_khop = []
    for ev in sorted(events, key=lambda e: e["thoi_gian"], reverse=True):
        muc = _giay(ev["thoi_gian"][11:])
        gan = min(gio_clip, key=lambda t: abs(_giay(t) - muc)) if gio_clip else None
        if gan is None or abs(_giay(gan) - muc) > lech_toi_da:
            khong_khop.append(ev)
            continue
        can_mo.setdefault(gan, []).append((ev, abs(_giay(gan) - muc)))
    khop = len(events) - len(khong_khop)
    log(u"  ghép được %d/%d sự kiện với clip." % (khop, len(events)))

    # An toan: neu ghep hong gan het thi day la loi doc giao dien, KHONG phai
    # do xe di sai huong -> giu nguyen moi su kien thay vi xoa sach bao cao.
    if khop < max(1, len(events) * 0.5):
        log(u"  (!) Ghép clip thất bại (%d/%d) – bỏ qua bước lọc hướng lần này, "
            u"giữ nguyên tất cả sự kiện." % (khop, len(events)))
        ui.tra_lai()
        return 0

    # ---- Buoc 3: cuon lai tu dau, mo dung nhung clip da chon ----
    xong = 0
    con_lai = dict(can_mo)
    len_dau_danh_sach(ui)
    for _vong in range(110):
        if not con_lai:
            break
        # So khop theo DO LECH GIAY chu khong so chuoi: hai lan OCR cung mot the
        # co the ra chuoi hoi khac nhau ("17:07:40" vs "17:07:4O").
        lam = None
        for c, t in _the_hien_tren_man(ui):
            khoa = _khop_gan(t, con_lai)
            if khoa:
                lam = (c, t, khoa)
                break
        if lam is None:
            ui.scroll(4)
            continue

        card, t, khoa = lam
        nhom = con_lai.pop(khoa)
        xa, ya, xb, yb = card
        ui.click((xa + xb) // 2, (ya + yb) // 2, double=True, settle=2.0)
        h = _cho_player()
        if h is None:
            log(u"  (!) Không mở được clip %s." % t)
            continue
        anh, det, huong, dx = chup_tu_player(h, detector, cfg)
        _close_player()

        for ev, lech in nhom:
            log(u"  → %s  ← clip %s (lệch %ds)%s"
                % (ev["thoi_gian"][11:], t, lech,
                   u"  ⚠ lệch nhiều" if lech > 60 else u""))
            if _loc_huong(ev, cfg, huong, dx, log) or anh is None:
                if anh is None:
                    log(u"     (!) Không chụp được khung hình.")
                continue
            ev["anh_net"] = anh
            ev["khung_xe"] = det.box if det is not None else None
            ev["tin_cay"] = round(float(det.conf), 3) if det is not None else None
            ev["loai_xe_net"] = det.label if det is not None else None
            xong += 1
            log(u"     ✔ ảnh %dx%d%s – hướng %s" % (
                anh.shape[1], anh.shape[0],
                u" – nhận ra %s %.0f%%" % (det.label, det.conf * 100) if det else u"",
                TEN_HUONG[huong] if huong else u"chưa rõ"))

    ui.tra_lai()                      # bo co "luon noi tren cung"

    # ---- Su kien khong co clip: khong the kiem tra huong ----
    sot = khong_khop + [ev for nhom in con_lai.values() for ev, _l in nhom]
    if sot:
        log(u"  (!) %d sự kiện không mở được clip tương ứng." % len(sot))
        for ev in sot:
            _khong_ro_huong(ev, cfg, log, u"không tìm thấy clip để kiểm tra hướng")
    return xong


def len_dau_danh_sach(ui, nac=220):
    """Cuon len dau danh sach.

    Mot ngay co the co hon 150 clip nen phai cuon that nhieu nac; cuon thieu se
    bat dau tu GIUA danh sach va bo sot toan bo phan tren.
    """
    ui.scroll(-nac)
    time.sleep(1.5)
    return True


def _khop_gan(gio, cac_khoa, dung_sai=3):
    """Tim khoa trong `cac_khoa` co gio lech khong qua `dung_sai` giay."""
    try:
        muc = _giay(gio)
    except Exception:
        return None
    for k in cac_khoa:
        if abs(_giay(k) - muc) <= dung_sai:
            return k
    return None


def _the_hien_tren_man(ui, thu=4):
    """Cac the clip dang hien + gio cua chung (cho anh thumbnail tai xong)."""
    for _ in range(thu):
        img = ui.shot()
        the = [(c, read_clip_time(img, c)) for c in find_clip_cards(img)]
        the = [(c, t) for c, t in the if t]
        if the:
            return the
        time.sleep(1.8)
    return []


def quet_danh_sach_clip(ui, log=None, toi_da=70):
    """Cuon het danh sach mot luot, ghi lai gio cua tat ca clip nhin thay.

    Dung lai khi CHAM DAY danh sach (man hinh khong doi sau khi cuon), chu khong
    dung khi gap man hinh trong - vi anh thumbnail co the chi dang tai cham.
    """
    thay = set()
    len_dau_danh_sach(ui)              # ve dau danh sach
    truoc, giong = None, 0
    for _ in range(toi_da):
        hien = set(t for _c, t in _the_hien_tren_man(ui))
        thay |= hien
        giong = giong + 1 if (hien and hien == truoc) else 0
        truoc = hien
        if giong >= 2:                 # cuoi danh sach
            break
        ui.scroll(4)
    return thay


def _khong_ro_huong(ev, cfg, log, ly_do):
    """Xu ly su kien khong xac dinh duoc huong theo cau hinh."""
    ev["huong"] = None
    if cfg.get("huong_xe", "ca_hai") == "ca_hai":
        return False
    if cfg.get("giu_khi_khong_ro_huong", False):
        return False
    ev["bo_qua"] = ly_do
    log(u"     ⏭ bỏ qua %s: %s" % (ev["thoi_gian"][11:], ly_do))
    return True


def _loc_huong(ev, cfg, huong, dx, log):
    """True neu su kien bi loai vi khong dung huong. Ghi luon ket qua vao ev."""
    ev["huong"] = huong
    ev["dx"] = round(float(dx), 1)
    mong_muon = cfg.get("huong_xe", "ca_hai")
    if mong_muon == "ca_hai":
        return False
    if huong is None:
        return _khong_ro_huong(ev, cfg, log,
                               u"xe dịch ngang quá ít, không rõ ra hay vào mỏ")
    if huong != mong_muon:
        ev["bo_qua"] = u"xe đi %s" % TEN_HUONG.get(huong, huong)
        log(u"     ⏭ bỏ qua: %s (lệch ngang %+.0f px)" % (ev["bo_qua"], dx))
        return True
    return False
