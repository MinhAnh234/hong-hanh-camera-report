# -*- coding: utf-8 -*-
"""Duyet lan luot cac clip ghi hinh bang nut '>' ngay trong cua so phat.

Vi sao lam cach nay: cach cu phai CUON mot danh sach hon 150 clip roi tim lai
dung the de bam - rat de truot (cuon thieu, anh thumbnail chua tai, OCR chu nho
doc lech). Cach moi chi dung danh sach DUNG MOT LAN de mo clip dau tien, sau do
di chuyen bang nut '>' va doc gio tu TIEU DE cua so phat - la chu giao dien ro
net nen doc gan nhu khong bao gio sai.

Voi moi clip: chup vai khung hinh, nhan dang xe, bam vet de biet xe di trai sang
phai (ra khoi mo) hay nguoc lai - chi de GHI CHU, khong dung de loc bo.
Moi clip co xe deu duoc ghi nhan, khong phan biet huong.
"""
import ctypes
import re
import time
from datetime import datetime

import cv2
import win32gui

from . import huy, ocr
from .capture import list_windows, print_window
from .clip_capture import (PLAYER_TITLE, TEN_HUONG, _cho_player, _close_player,
                           chon_tab_ban_ghi, chup_tu_player, find_clip_cards,
                           read_clip_time)
from .imou_events import ImouUI

user32 = ctypes.windll.user32
_GIO_CUOI = re.compile(r"(\d{1,2}):(\d{2}):(\d{2})\s*$")

# Vi tri (theo ty le cua so phat) cua cac nut
NUT_KE_TIEP = (0.988, 0.50)        # '>' chuyen sang clip cu hon
NUT_TRUOC = (0.012, 0.50)          # '<' chuyen sang clip moi hon
VUNG_TIEU_DE = (0.030, 0.075, 0.0, 0.22)     # (y1, y2, x1, x2) theo ty le


class ChuaCoClip(RuntimeError):
    """Ngay dang chon chua co clip ghi hinh nao.

    Chuyen binh thuong khi lich chay tu dong quet vao dau ngay moi (camera
    chua kip ghi clip) - khong phai loi, nen chi bao mot dong thay vi do ca
    traceback ra nhat ky."""


def doc_gio_clip(hwnd):
    """Doc gio bat dau cua clip tu tieu de cua so phat -> 'HH:MM:SS'."""
    p = print_window(hwnd)
    if p is None:
        return None
    ph, pw = p.shape[:2]
    y1, y2, x1, x2 = VUNG_TIEU_DE
    dau = p[int(ph * y1):int(ph * y2), int(pw * x1):int(pw * x2)]
    for scale in (3.0, 4.0, 2.5):
        gon = ocr.read_text(dau, scale=scale).replace("\n", " ").replace(" ", "")
        m = _GIO_CUOI.search(gon)
        if m:
            g, p_, s = (int(v) for v in m.groups())
            if g <= 23 and p_ <= 59 and s <= 59:
                return "%02d:%02d:%02d" % (g, p_, s)
    return None


def _bam(hwnd, vi_tri, cho=2.5):
    l, t, r, b = win32gui.GetWindowRect(hwnd)
    x = int(l + vi_tri[0] * (r - l))
    y = int(t + vi_tri[1] * (b - t))
    user32.SetCursorPos(x, y)
    time.sleep(0.35)
    user32.mouse_event(0x0002, 0, 0, 0, 0)
    time.sleep(0.08)
    user32.mouse_event(0x0004, 0, 0, 0, 0)
    time.sleep(0.25)
    user32.SetCursorPos(int(l + (r - l) * 0.5), b - 6)    # bo chuot khoi nut
    time.sleep(cho)


def sang_clip_ke_tiep(hwnd, gio_hien_tai, thu=3):
    """Bam '>' cho den khi tieu de doi sang clip khac. Tra ve gio moi hoac None."""
    for _ in range(thu):
        _bam(hwnd, NUT_KE_TIEP)
        moi = doc_gio_clip(hwnd)
        if moi and moi != gio_hien_tai:
            return moi
    return None


def mo_clip_moi_nhat(ui, cfg, ngay, log=print):
    """Vao Xem Lai > Ban ghi noi bo > dung ngay, mo clip DAU TIEN (moi nhat)."""
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
        raise RuntimeError(u"Không chọn được ngày %d (đang mở ngày %s)."
                           % (ngay.day, ui.ngay_dang_chon()))
    time.sleep(2.0)

    for _ in range(6):
        img = ui.shot()
        the = [(c, read_clip_time(img, c)) for c in find_clip_cards(img)]
        the = [(c, t) for c, t in the if t]
        if the:
            xa, ya, xb, yb = the[0][0]
            ui.click((xa + xb) // 2, (ya + yb) // 2, double=True, settle=2.5)
            h = _cho_player()
            if h:
                return h
        time.sleep(2.0)
    raise ChuaCoClip(u"Ngày %s chưa có clip ghi hình nào."
                     % ngay.strftime("%d-%m-%Y"))


def _giay(hms):
    g, p, s = (int(v) for v in hms.split(":"))
    return g * 3600 + p * 60 + s


def la_anh_ban_dem(anh, nguong_bao_hoa=25):
    """Anh co phai chup o che do BAN DEM (hong ngoai) khong.

    Ban dem camera tat loc mau va bat den hong ngoai nen anh gan nhu don sac:
    do bao hoa mau trung binh tut ve gan 0, trong khi anh ban ngay luon tren 40.
    Dua vao chinh anh chac chan hon la chia theo khung gio co dinh, vi gio troi
    sang/toi thay doi theo mua.
    """
    if anh is None or anh.size == 0:
        return False
    hsv = cv2.cvtColor(anh, cv2.COLOR_BGR2HSV)
    return float(hsv[:, :, 1].mean()) < float(nguong_bao_hoa)


def mo_clip_cu_hon(ui, gio_moc, log=print, so_lan_cuon=40):
    """Quay lai danh sach, cuon xuong tim clip CU HON `gio_moc` roi mo no.

    Danh sach clip tai dan (lazy load) nen nut '>' chi di duoc trong pham vi
    giao dien da tai san - het pham vi do la nut khong doi clip nua du danh sach
    con rat nhieu. Luc do phai cuon cho tai them roi mo tay clip ke tiep.

    Tra ve hwnd cua so phat, hoac None neu that su het clip.
    """
    moc = _giay(gio_moc)
    for _ in range(so_lan_cuon):
        huy.kiem_tra()
        img = ui.shot()
        ung_vien = []
        for c in find_clip_cards(img):
            t = read_clip_time(img, c)
            if t and _giay(t) < moc:
                ung_vien.append((_giay(t), t, c))
        if ung_vien:
            _g, t, card = max(ung_vien)        # clip cu hon nhung gan moc nhat
            xa, ya, xb, yb = card
            ui.click((xa + xb) // 2, (ya + yb) // 2, double=True, settle=2.0)
            h = _cho_player()
            if h is not None:
                log(u"  … cuộn danh sách, mở tiếp clip %s" % t)
                return h
        ui.scroll(4)
        time.sleep(0.8)
    return None


def gop_luot_trung(events, khoang, log=print):
    """Gop cac luot sat nhau (cung mot xe bi cat lam doi giua hai clip).

    `events` phai da sap xep theo thoi gian tang dan. Trong moi nhom giu lai
    luot co do tin cay cao nhat - do thuong la khung hinh xe vao giua khung.
    KHONG gop hai luot da xac dinh duoc huong ma NGUOC nhau: do chac chan la
    hai chiec xe khac nhau di nguoc chieu.
    """
    if khoang <= 0 or len(events) < 2:
        return events

    def giay(e):
        h, p, s = (int(v) for v in e["thoi_gian"][11:].split(":"))
        return h * 3600 + p * 60 + s

    giu, bo, i = [], [], 0
    while i < len(events):
        nhom, j = [events[i]], i + 1
        while j < len(events):
            if giay(events[j]) - giay(nhom[-1]) > khoang:
                break
            ha, hb = nhom[-1].get("huong"), events[j].get("huong")
            if ha and hb and ha != hb:      # hai xe di nguoc chieu
                break
            nhom.append(events[j])
            j += 1
        tot = max(nhom, key=lambda e: e.get("tin_cay") or e.get("do_tin_cay") or 0)
        giu.append(tot)
        bo.extend(e for e in nhom if e is not tot)
        i = j
    if bo:
        log(u"• Gộp %d lượt trùng (cùng xe bị cắt làm đôi giữa hai clip)." % len(bo))
        for e in bo:
            log(u"    ↳ bỏ %s" % e["thoi_gian"][11:])
    return giu


def gop_xe_dung_yen(events, phut, lech, log=print, khoa_khung="khung_xe"):
    """Gop cac luot lien tiep ma KHUNG XE nam gan nhu cung mot cho.

    Mot chiec xe do lai giua khung hinh se hien ra o hang chuc clip lien tiep,
    moi clip thanh mot "luot", du no chi la MOT lan xe vao mo. Khac voi xe dang
    chay - tam khung dich hang tram diem anh giua hai clip - xe dung yen co tam
    khung gan nhu khong doi.

    `events` phai da sap xep theo thoi gian tang dan.
    """
    if phut <= 0 or lech <= 0 or len(events) < 2:
        return events

    def giay(e):
        h, p, s = (int(v) for v in e["thoi_gian"][11:].split(":"))
        return h * 3600 + p * 60 + s

    def tam(e):
        k = e.get(khoa_khung) or e.get("khung")
        if not k:
            return None
        x, y, w, h = k
        return x + w // 2, y + h // 2

    giu, bo, i = [], [], 0
    while i < len(events):
        nhom, j = [events[i]], i + 1
        while j < len(events):
            if giay(events[j]) - giay(nhom[-1]) > phut * 60:
                break
            a, b = tam(nhom[-1]), tam(events[j])
            if a is None or b is None:
                break
            if abs(a[0] - b[0]) > lech or abs(a[1] - b[1]) > lech:
                break
            nhom.append(events[j])
            j += 1
        tot = max(nhom, key=lambda e: e.get("tin_cay") or e.get("do_tin_cay") or 0)
        giu.append(tot)
        bo.extend(e for e in nhom if e is not tot)
        i = j
    if bo:
        log(u"• Gộp %d lượt xe đỗ tại chỗ (khung không nhúch nhích)." % len(bo))
        for e in bo:
            log(u"    ↳ bỏ %s" % e["thoi_gian"][11:])
    return giu


def duyet(cfg, ngay, log=print, dung_truoc=None, toi_da=250):
    """Duyet cac clip cua `ngay` tu moi den cu.

    dung_truoc: 'HH:MM:SS' - gap clip cu hon moc nay thi dung (dung cho lan quet
                sau chi lay phan moi).
    Tra ve danh sach su kien: [{'thoi_gian', 'anh_net', 'khung_xe', ...}]
    """
    from .detector import VehicleDetector

    try:
        detector = VehicleDetector(cfg)
    except Exception as e:
        raise RuntimeError(u"Không nạp được mô hình nhận dạng: %s" % e)

    ui = ImouUI(cfg)
    if not ui.attach():
        raise RuntimeError(ui.cap.last_error or u"Không tìm thấy cửa sổ Imou.")
    _close_player()

    try:
        hwnd = mo_clip_moi_nhat(ui, cfg, ngay, log)
    except ChuaCoClip as e:
        log(u"  %s" % e)
        ui.tra_lai()
        return []
    ImouUI.dua_len_tren(hwnd, True)

    mong_muon = cfg.get("huong_xe", "ca_hai")
    bo_tu_gio = int(cfg.get("khong_quet_tu_gio", 0) or 0)
    ket_qua, da_xem = [], 0
    gio = doc_gio_clip(hwnd)
    log(u"• Bắt đầu từ clip %s, duyệt bằng nút ›…" % gio)

    while gio and da_xem < toi_da:
        huy.kiem_tra()
        da_xem += 1
        if dung_truoc and _giay(gio) < _giay(dung_truoc):
            log(u"  đã tới mốc %s – dừng." % dung_truoc)
            break

        if bo_tu_gio and int(gio[:2]) >= bo_tu_gio:
            # Ngoai gio theo doi: bo qua LUON, khong can phat clip -> nhanh hon
            # rat nhieu vi buoi toi van co hang chuc clip.
            log(u"  %s  – ngoài giờ theo dõi (từ %02d:00) – bỏ qua"
                % (gio, bo_tu_gio))
            moi = sang_clip_ke_tiep(hwnd, gio)
            if moi is None:
                _close_player()
                h = mo_clip_cu_hon(ui, gio, log)
                if h is None:
                    log(u"  hết clip.")
                    break
                hwnd = h
                ImouUI.dua_len_tren(hwnd, True)
                moi = doc_gio_clip(hwnd)
                if moi is None or _giay(moi) >= _giay(gio):
                    log(u"  hết clip.")
                    break
            gio = moi
            continue

        anh, det, huong, dx = chup_tu_player(hwnd, detector, cfg,
                                             so_khung=14, moi_khung=0.8,
                                             cho_toi_da=10.0)
        nguong_dem = float(cfg.get("nguong_tin_cay_ban_dem", 0.5))
        if det is None:
            log(u"  %s  – không thấy xe" % gio)
        elif (nguong_dem > 0
              and la_anh_ban_dem(anh, cfg.get("nguong_bao_hoa_dem", 25))
              and (nguong_dem >= 1.0 or det.conf < nguong_dem)):
            log(u"  %s  – %s %.0f%%, ảnh ban đêm tin cậy thấp – bỏ"
                % (gio, det.label, det.conf * 100))
        elif (huong is None
              and det.conf < float(cfg.get("nguong_tin_cay_khong_ro_huong", 0.70))):
            log(u"  %s  – %s %.0f%%, không dịch chuyển và nhận dạng yếu – bỏ"
                % (gio, det.label, det.conf * 100))
        elif mong_muon != "ca_hai" and huong != mong_muon:
            log(u"  %s  – %s, bỏ (%s)"
                % (gio, det.label, TEN_HUONG.get(huong, u"chưa rõ hướng")))
        else:
            ket_qua.append({
                "thoi_gian": "%s %s" % (ngay.strftime("%Y-%m-%d"), gio),
                "anh_net": anh, "khung_xe": det.box,
                "tin_cay": round(float(det.conf), 3), "loai_xe_net": det.label,
                "huong": huong, "dx": round(float(dx), 1),
            })
            log(u"  %s  ✔ %s %.0f%% – %s"
                % (gio, det.label, det.conf * 100,
                   TEN_HUONG.get(huong, u"chưa rõ hướng")))

        moi = sang_clip_ke_tiep(hwnd, gio)
        if moi is None:
            # Het pham vi clip da tai -> ve danh sach, cuon them roi mo tiep.
            _close_player()
            h = mo_clip_cu_hon(ui, gio, log)
            if h is None:
                log(u"  hết clip.")
                break
            hwnd = h
            ImouUI.dua_len_tren(hwnd, True)
            moi = doc_gio_clip(hwnd)
            if moi is None or _giay(moi) >= _giay(gio):
                log(u"  hết clip (không tìm được clip cũ hơn %s)." % gio)
                break
        gio = moi

    _close_player()
    ui.tra_lai()
    log(u"• Đã duyệt %d clip, ghi nhận %d lượt xe."
        % (da_xem, len(ket_qua)))
    return ket_qua
