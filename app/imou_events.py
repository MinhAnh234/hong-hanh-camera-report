# -*- coding: utf-8 -*-
"""Doc SU KIEN PHAT HIEN PHUONG TIEN san co cua camera Imou.

Camera AOV PT-BE57 tu no da co AI phat hien phuong tien: moi lan co xe, camera
ghi lai mot su kien kem anh chup va moc thoi gian. App Imou tren may tinh hien
danh sach nay o "Trung tam tin nhan".

Module nay dieu khien giao dien Imou (bam chuot) de:
    mo trung tam tin nhan -> chon camera -> loc "Phat Hien Phuong Tien"
    -> chon ngay -> quet toan bo the su kien (co cuon trang)

Moc thoi gian doc bang OCR co san cua Windows (app/ocr.py).
"""
import ctypes
import time
from datetime import datetime, timedelta

import cv2
import numpy as np
import win32con
import win32gui

from . import digits, huy, ocr
from .capture import WindowCapture, content_scale, enable_dpi_awareness

user32 = ctypes.windll.user32
BS_N = chr(10)          # ky tu xuong dong

# Vi tri cac bieu tuong tren thanh tieu de, tinh tu MEP PHAI cua cua so (diem anh).
ICON_MESSAGE_DX = 173
ICON_MESSAGE_Y = 21


class ImouUI(object):
    """Lop dieu khien cua so Imou: bam chuot, cuon, chup lai man hinh."""

    def __init__(self, cfg):
        enable_dpi_awareness()
        self.cfg = cfg
        self.cap = WindowCapture(cfg)
        self.rect = None
        # He so doi toa do anh -> toa do cua so (khac 1.0 khi man hinh phong to)
        self._sx = 1.0
        self._sy = 1.0

    # ---------- co ban ----------
    @staticmethod
    def dua_len_tren(hwnd, giu=True):
        """Ep cua so noi len tren cung.

        SetForegroundWindow thuong bi Windows chan khi goi tu tien trinh nen,
        nen cua so Imou van nam duoi cua so khac va cu chuot bam nham vao do.
        Dat co HWND_TOPMOST thi luon nang duoc cua so len.
        """
        co = win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetWindowPos(
                hwnd, win32con.HWND_TOPMOST if giu else win32con.HWND_NOTOPMOST,
                0, 0, 0, 0, co)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            pass

    def len_tren(self):
        if self.hwnd:
            self.dua_len_tren(self.hwnd, True)
            time.sleep(0.35)

    def tra_lai(self):
        if self.hwnd:
            self.dua_len_tren(self.hwnd, False)

    def attach(self):
        if not self.cap.attach():
            return False
        self.hwnd = self.cap.hwnd
        self.dua_len_tren(self.hwnd, True)
        time.sleep(0.6)
        self.rect = win32gui.GetWindowRect(self.hwnd)
        return True

    @property
    def size(self):
        l, t, r, b = win32gui.GetWindowRect(self.hwnd)
        self.rect = (l, t, r, b)
        return r - l, b - t

    def shot(self, thu_lai=6):
        """Chup ca cua so. Thu lai vai lan vi luc cua so vua doi trang thai
        (nang len tren, doi kich thuoc) PrintWindow co the tra ve rong."""
        err = u""
        for lan in range(thu_lai):
            img, err = self.cap.grab_full()
            if img is not None:
                self._sx, self._sy = content_scale(self.hwnd, img)
                return img
            time.sleep(0.6)
            if lan == thu_lai // 2:
                self.cap.attach()
                self.hwnd = self.cap.hwnd
        raise RuntimeError(err or u"Không chụp được cửa sổ Imou.")

    def click(self, x, y, double=False, settle=1.4, park=True):
        """x, y la toa do tren ANH chup duoc (khong phai toa do man hinh)."""
        self.len_tren()
        l, t = self.rect[0], self.rect[1]
        user32.SetCursorPos(int(l + x * self._sx), int(t + y * self._sy))
        time.sleep(0.3)
        for _ in range(2 if double else 1):
            user32.mouse_event(0x0002, 0, 0, 0, 0)
            time.sleep(0.07)
            user32.mouse_event(0x0004, 0, 0, 0, 0)
            time.sleep(0.1)
        if park:
            w, h = self.size
            user32.SetCursorPos(int(l + w - 6), int(t + h - 6))
        time.sleep(settle)

    def scroll(self, notches, at=None):
        self.len_tren()
        l, t = self.rect[0], self.rect[1]
        w, h = self.size
        px, py = at or (int(w * 0.62), int(h * 0.55))
        user32.SetCursorPos(int(l + px), int(t + py))     # da la toa do cua so
        time.sleep(0.25)
        for _ in range(abs(notches)):
            user32.mouse_event(0x0800, 0, 0, ctypes.c_int(-120 if notches > 0 else 120), 0)
            time.sleep(0.1)
        time.sleep(2.2)          # cho danh sach tai xong anh sau khi cuon

    # ---------- dieu huong ----------
    def open_message_center(self):
        """Mo trung tam tin nhan. True neu da o trong do."""
        if self._in_message_center():
            return True
        w = self.shot().shape[1]          # be ngang tinh tren ANH
        self.click(w - ICON_MESSAGE_DX, ICON_MESSAGE_Y, settle=2.0)
        if self._in_message_center():
            return True
        # thu lech mot chut phong khi bo bieu tuong khac nhau
        for dx in (ICON_MESSAGE_DX - 12, ICON_MESSAGE_DX + 12):
            self.click(w - dx, ICON_MESSAGE_Y, settle=1.8)
            if self._in_message_center():
                return True
        return False

    def _in_message_center(self):
        head = self.shot()[80:230, 260:]
        lines = ocr.read(head, scale=1.6)
        return (ocr.find_line(lines, u"ngay", u"gan") is not None
                or ocr.find_line(lines, u"tat", u"ca") is not None)

    SIDEBAR_W = 260          # be ngang thanh danh sach thiet bi (co dinh)

    def _find_device_line(self, name):
        img = self.shot()
        side = img[220:, :self.SIDEBAR_W]
        lines = ocr.read(side, scale=2.0)
        key = name.split()[0]                     # vd "AOV"
        hit = ocr.find_line(lines, key)
        if hit is None and len(name) >= 6:
            hit = ocr.find_line(lines, name[:6])
        return hit

    def select_device(self, name):
        """Chon camera trong danh sach ben trai; tu cuon neu chua thay."""
        for buoc in range(8):
            hit = self._find_device_line(name)
            if hit is not None:
                cx, cy = hit.center
                self.click(cx, cy + 220, settle=2.4)
                return True
            if buoc < 5:
                self.scroll(3, at=(self.SIDEBAR_W // 2, 400))     # cuon xuong
            else:
                self.scroll(-6, at=(self.SIDEBAR_W // 2, 400))    # cuon nguoc len
        return False

    def set_filter(self, keyword=u"tien"):
        """Mo o loc loai su kien va chon dung loai."""
        img = self.shot()
        band = img[170:225, 265:700]
        lines = ocr.read(band, scale=2.2)
        drop = (ocr.find_line(lines, u"tatca") or ocr.find_line(lines, u"phat", u"hien")
                or (lines[0] if lines else None))
        if drop is None:
            return False
        cx, cy = drop.center
        self.click(cx + 265, cy + 170, settle=1.6)

        menu = self.shot()[210:470, 265:600]
        mlines = ocr.read(menu, scale=2.2)
        opt = ocr.find_line(mlines, keyword)
        if opt is None:
            self.click(cx + 265, cy + 170, settle=1.0)   # dong menu
            return False
        ox, oy = opt.center
        self.click(ox + 265, oy + 210, settle=2.2)
        return True

    DAY_BAND = (85, 132, 380)          # (y1, y2, x1) dai chua so ngay

    def day_tabs(self, img=None):
        """Cac the ngay tren dau trang -> [(so_ngay, x, y, dang_chon)].

        Luu y: canh so ngay con co mot cham tron mau cam (bao "ngay nay co du
        lieu"), OCR hay doc thanh ky tu la -> phai loc lay rieng phan chu so.
        Va the DANG CHON thi chinh CHU SO duoc to mau cam.
        """
        img = self.shot() if img is None else img
        y1, y2, x1 = self.DAY_BAND
        band = img[y1:y2, x1:]
        hsv = cv2.cvtColor(band, cv2.COLOR_BGR2HSV)
        out = []
        for ln in ocr.read(band, scale=2.5):
            if "-" in ln.text or "/" in ln.text:
                continue                      # do la nhan ngay "2026-08-24"
            tu = ln.words[0] if ln.words else None
            if tu is None:
                continue
            so = "".join(c for c in tu.text if c.isdigit())
            if not (1 <= len(so) <= 2) or not (1 <= int(so) <= 31):
                continue
            bx, by, bw, bh = tu.box
            o = hsv[max(0, by):by + bh, max(0, bx):bx + bw]
            dang_chon = bool(o.size) and float(o[:, :, 1].mean()) > 60
            out.append((int(so), bx + bw // 2 + x1, by + bh // 2 + y1, dang_chon))
        if len(out) >= 3:
            # cac the ngay nam tren cung mot hang -> loai chu so lac tu cho khac
            ys = sorted(t[2] for t in out)
            giua = ys[len(ys) // 2]
            out = [t for t in out if abs(t[2] - giua) <= 10]
        out.sort()
        return out

    def ngay_dang_chon(self, img=None):
        for d, _x, _y, chon in self.day_tabs(img):
            if chon:
                return d
        return None

    def cho_ngay(self, day, giay=10.0):
        """Cho den khi the ngay `day` thuc su duoc chon (trang dang tai lai)."""
        het = time.time() + giay
        while time.time() < het:
            if self.ngay_dang_chon() == day:
                return True
            time.sleep(1.2)
        return False

    def select_day(self, day, thu=4):
        """Chon dung ngay va XAC MINH lai; tu lat trang neu ngay chua hien.

        Rat quan trong: neu bam hut ma khong kiem tra thi se lay nham du lieu
        cua ngay khac ma khong hay biet.
        """
        for lan in range(thu):
            tabs = self.day_tabs()
            if not tabs:
                time.sleep(1.5)
                continue
            if self.ngay_dang_chon() == day:
                return True

            dung = [t for t in tabs if t[0] == day]
            if dung:
                _d, x, y, _c = dung[0]
                self.click(x, y, settle=2.6)
                if self.cho_ngay(day):        # trang tai lai -> phai cho roi moi kiem tra
                    return True
                continue

            # ngay can tim khong nam trong dai dang hien -> lat sang trai/phai
            nho_nhat = min(t[0] for t in tabs)
            lui = day < nho_nhat or day > max(t[0] for t in tabs)
            if not lui:
                continue
            x_mui_ten = min(t[1] for t in tabs) - 58        # nut '<' truoc the dau
            if day > max(t[0] for t in tabs):
                x_mui_ten = max(t[1] for t in tabs) + 58     # nut '>' sau the cuoi
            self.click(x_mui_ten, tabs[0][2], settle=2.2)
        return False

    # ---------- quet the su kien ----------
    @staticmethod
    def find_cards(img):
        """Tim anh thumbnail cua tung the su kien -> [(x, y, w, h)]."""
        H, W = img.shape[:2]
        x0, y0 = 265, 220
        area = img[y0:H - 8, x0:W - 8]
        hsv = cv2.cvtColor(area, cv2.COLOR_BGR2HSV)
        mask = ((hsv[:, :, 1] > 35) & (hsv[:, :, 2] > 40)).astype(np.uint8) * 255
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9)))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in cnts:
            x, y, w, h = cv2.boundingRect(c)
            if w < 60 or h < 40:
                continue
            if not (1.2 < w / float(h) < 2.2):
                continue
            boxes.append((x + x0, y + y0, w, h))
        boxes.sort(key=lambda b: (b[1] // 30, b[0]))
        return boxes

    @staticmethod
    def time_strip(img, box):
        """Dai chu chua moc thoi gian, nam ben phai thumbnail."""
        x, y, w, h = box
        return img[max(0, y + h - 26):y + h + 4, x + w + 2:x + w + 152]

    def read_card_time(self, img, box, dr=None, ngay_biet=None):
        """Doc moc thoi gian cua mot the. -> (chuoi thoi gian, chac_chan)

        Ket hop hai cach doc de bu khuyet diem cho nhau:
          - OCR Windows doc nhieu lan (lech vai diem anh, nhieu do phong) roi
            BO PHIEU  -> chiu duoc nhieu, nhung hay lan 5/6 o co chu nho.
          - Doi sanh mau chu so (digits.py) -> chinh xac tuyet doi khi tach duoc
            ky tu, nen chi ghi de ket qua OCR khi do giong rat cao.
        """
        strip = self.time_strip(img, box)
        if strip.size == 0:
            return None, False

        votes = {}
        for dx in (0, 1, 2):
            for scale in (8.0, 10.0):
                s2 = img[max(0, box[1] + box[3] - 26):box[1] + box[3] + 4,
                         box[0] + box[2] + 2 + dx:box[0] + box[2] + 152 + dx]
                text = ocr.read_text(s2, scale=scale).replace(BS_N, " ")
                got = ocr.parse_timestamp(text)
                if got:
                    diem = 2 if len([c for c in text if c.isdigit()]) == 14 else 1
                    votes[got] = votes.get(got, 0) + diem
        ocr_ts = max(votes.items(), key=lambda kv: kv[1])[0] if votes else None

        if dr is None:
            return ocr_ts, bool(ocr_ts)

        goi_y = None
        if ocr_ts:
            goi_y = "".join(c for c in ocr_ts if c.isdigit())
            goi_y = goi_y if len(goi_y) == 14 else None
        chuoi, diem = dr.doc_day(strip, ngay_biet=ngay_biet, goi_y=goi_y)
        if chuoi and diem >= 0.85:
            ts = "%s-%s-%s %s:%s:%s" % (chuoi[0:4], chuoi[4:6], chuoi[6:8],
                                        chuoi[8:10], chuoi[10:12], chuoi[12:14])
            return ts, True
        return ocr_ts, False

    def wait_for_cards(self, timeout=10.0):
        """Cho danh sach su kien hien ra sau khi doi bo loc / doi ngay."""
        het = time.time() + timeout
        while time.time() < het:
            img = self.shot()
            if self.find_cards(img):
                return img
            time.sleep(0.8)
        return None

    def scrape(self, max_scrolls=30, on_found=None, log=None, ngay_biet=None):
        """Quet toan bo su kien trong danh sach (tu cuon xuong het). -> [dict]"""
        seen = {}
        dr = digits.DigitReader()
        img = self.wait_for_cards()
        if img is None:
            return []

        khong_moi = 0
        for vong in range(max_scrolls + 1):
            huy.kiem_tra()
            if img is None:
                img = self.shot()
            them = 0
            for box in self.find_cards(img):
                huy.kiem_tra()
                ts, chac = self.read_card_time(img, box, dr=dr, ngay_biet=ngay_biet)
                if not ts or ts in seen:
                    continue
                x, y, w, h = box
                ev = {"thoi_gian": ts, "chac_chan": chac,
                      "anh": img[y:y + h, x:x + w].copy()}
                seen[ts] = ev
                them += 1
                if on_found:
                    on_found(ev)
            if log:
                log(u"    vòng %d: +%d sự kiện (tổng %d)" % (vong + 1, them, len(seen)))
            khong_moi = 0 if them else khong_moi + 1
            if khong_moi >= 2 and seen:
                break
            if khong_moi >= 4:
                break
            self.scroll(4)
            img = None
        return [seen[k] for k in sorted(seen)]


def thu_thap(cfg, ngay=None, on_found=None, log=print):
    """Lay danh sach su kien phuong tien cua mot ngay.

    ngay: doi tuong date (mac dinh = hom nay).
    """
    ngay = ngay or datetime.now().date()
    ui = ImouUI(cfg)
    if not ui.attach():
        raise RuntimeError(ui.cap.last_error or u"Không tìm thấy cửa sổ Imou.")

    log(u"• Mở trung tâm tin nhắn…")
    if not ui.open_message_center():
        # App vua khoi dong co the con dang tai du lieu -> cho roi thu lai
        for lan in (1, 2):
            log(u"  chưa vào được, chờ 10 giây rồi thử lại (lần %d)…" % lan)
            time.sleep(10)
            ui.attach()
            if ui.open_message_center():
                break
        else:
            raise RuntimeError(u"Không mở được trung tâm tin nhắn của Imou.")

    ten = cfg.get("camera_name", "")
    log(u"• Chọn camera %s…" % ten)
    if not ui.select_device(ten):
        raise RuntimeError(u"Không tìm thấy camera '%s' trong danh sách." % ten)

    log(u"• Lọc loại sự kiện: Phát Hiện Phương Tiện…")
    if not ui.set_filter(u"tien"):
        log(u"  (!) Không đặt được bộ lọc – sẽ đọc tất cả loại sự kiện.")

    log(u"• Chọn ngày %s…" % ngay.strftime("%d-%m-%Y"))
    if not ui.select_day(ngay.day):
        raise RuntimeError(
            u"Không chọn được ngày %d trong Imou (đang mở ngày %s). "
            u"Dừng lại để tránh lấy nhầm dữ liệu của ngày khác."
            % (ngay.day, ui.ngay_dang_chon()))

    log(u"• Đang quét danh sách sự kiện…")
    try:
        events = ui.scrape(on_found=on_found, log=log,
                           ngay_biet=ngay.strftime("%Y%m%d"))
    finally:
        ui.tra_lai()

    # Tat ca the deu thuoc ngay dang chon -> ep lai phan NGAY theo tab da bam,
    # chi tin phan GIO doc duoc. Tranh truong hop OCR doc nham nam (2025/2026).
    pre = ngay.strftime("%Y-%m-%d")
    gom = {}
    for e in events:
        e["thoi_gian"] = pre + e["thoi_gian"][10:]
        gom[e["thoi_gian"]] = e
    return [gom[k] for k in sorted(gom)]


def ngay_tu_chuoi(s):
    """'23' | '23-08' | '2026-08-23' | 'hom-nay' | 'hom-qua' -> date"""
    s = (s or "").strip().lower()
    today = datetime.now().date()
    if s in ("", "hom-nay", "homnay", "today"):
        return today
    if s in ("hom-qua", "homqua", "yesterday"):
        return today - timedelta(days=1)
    parts = [p for p in s.replace("/", "-").split("-") if p]
    try:
        if len(parts) == 1:
            return today.replace(day=int(parts[0]))
        if len(parts) == 2:
            return today.replace(month=int(parts[1]), day=int(parts[0]))
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            return datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
    except ValueError:
        pass
    raise ValueError(u"Không hiểu ngày: %r" % s)
