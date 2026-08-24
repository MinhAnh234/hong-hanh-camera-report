# -*- coding: utf-8 -*-
"""Chup khung hinh tu cua so Imou va cat ra vung video (ROI).

Hai che do chup:
  - "printwindow": goi PrintWindow cua Windows -> chup duoc CA KHI cua so bi che
    khuat hoac nam duoi cua so khac. Day la che do uu tien.
  - "manhinh": chup vung man hinh (mss) - can cua so Imou hien ro tren cung.
"""
import ctypes
import os
import subprocess
import time
from ctypes import wintypes

import cv2
import mss
import numpy as np
import win32con
import win32gui
import win32process

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32


def enable_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            user32.SetProcessDPIAware()
        except Exception:
            pass


class _BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD), ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG), ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG), ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


class _BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", _BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def print_window(hwnd, flag=2):
    """Chup noi dung cua so bang PrintWindow. flag=2 = PW_RENDERFULLCONTENT."""
    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
    except Exception:
        return None
    w, h = r - l, b - t
    if w < 50 or h < 50:
        return None

    hdc = user32.GetWindowDC(hwnd)
    if not hdc:
        return None
    mem = gdi32.CreateCompatibleDC(hdc)
    bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
    old = gdi32.SelectObject(mem, bmp)
    try:
        if not user32.PrintWindow(hwnd, mem, flag):
            return None
        bi = _BITMAPINFO()
        bi.bmiHeader.biSize = ctypes.sizeof(_BITMAPINFOHEADER)
        bi.bmiHeader.biWidth = w
        bi.bmiHeader.biHeight = -h          # am = anh xuoi tu tren xuong
        bi.bmiHeader.biPlanes = 1
        bi.bmiHeader.biBitCount = 32
        bi.bmiHeader.biCompression = 0      # BI_RGB
        buf = ctypes.create_string_buffer(w * h * 4)
        if not gdi32.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0):
            return None
        arr = np.frombuffer(buf, dtype=np.uint8).reshape(h, w, 4)
        return _crop_content(cv2.cvtColor(arr, cv2.COLOR_BGRA2BGR))
    finally:
        gdi32.SelectObject(mem, old)
        gdi32.DeleteObject(bmp)
        gdi32.DeleteDC(mem)
        user32.ReleaseDC(hwnd, hdc)


def _crop_content(img):
    """Bo phan vien den thua cua anh PrintWindow.

    Khi man hinh dat ty le phong to (vd 125%) va app khong ho tro DPI, Windows
    ve noi dung o kich thuoc goc vao mot bitmap lon hon -> thua vien den ben
    phai/duoi. Cat bo phan thua de moi tinh toan sau do dung tren noi dung that.
    """
    if img is None or img.size == 0:
        return img
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    cols = np.where(gray.max(axis=0) > 8)[0]
    rows = np.where(gray.max(axis=1) > 8)[0]
    if len(cols) == 0 or len(rows) == 0:
        return img
    w, h = int(cols[-1]) + 1, int(rows[-1]) + 1
    if w < img.shape[1] * 0.5 or h < img.shape[0] * 0.5:
        return img                      # khac thuong -> giu nguyen
    if w == img.shape[1] and h == img.shape[0]:
        return img
    return img[:h, :w].copy()


def content_scale(hwnd, img):
    """He so doi toa do tren ANH sang toa do tren CUA SO (thuong 1.0 hoac 1.25)."""
    try:
        l, t, r, b = win32gui.GetWindowRect(hwnd)
    except Exception:
        return 1.0, 1.0
    h, w = img.shape[:2]
    if w < 10 or h < 10:
        return 1.0, 1.0
    return (r - l) / float(w), (b - t) / float(h)


def list_windows(title_part):
    """Danh sach cua so hien co tieu de chua title_part, lon truoc nho sau."""
    found = []

    def cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        text = win32gui.GetWindowText(hwnd) or ""
        if title_part.lower() in text.lower():
            l, t, r, b = win32gui.GetWindowRect(hwnd)
            if (r - l) > 300 and (b - t) > 300:
                found.append((hwnd, (r - l) * (b - t)))

    win32gui.EnumWindows(cb, None)
    found.sort(key=lambda x: -x[1])
    return [h for h, _ in found]


def restore_windows(title_part):
    """Khoi phuc cua so dang thu nho (minimize). Tra ve so cua so da khoi phuc.

    Cua so thu nho co toa do -32000 nen khong lot qua bo loc cua list_windows.
    """
    hits = []

    def cb(hwnd, _):
        text = win32gui.GetWindowText(hwnd) or ""
        if title_part.lower() in text.lower() and win32gui.IsIconic(hwnd):
            hits.append(hwnd)

    win32gui.EnumWindows(cb, None)
    for hwnd in hits:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        except Exception:
            pass
    return len(hits)


def dang_chay(ten_exe="Imou_en.exe"):
    """App da chay chua (du cua so co the dang an)."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq " + ten_exe],
            stderr=subprocess.DEVNULL, creationflags=0x08000000).decode("utf-8", "ignore")
        return ten_exe.lower() in out.lower()
    except Exception:
        return False


def mo_app_imou(cfg, log=None):
    """Mo app Imou neu chua co cua so nao. Tra ve True neu cuoi cung da co cua so.

    Dung cho lich chay tu dong: neu ai do da tat app Imou thi tu bat lai.
    """
    title = cfg.get("window_title", "Imou")
    noi = log or (lambda *_a: None)

    if list_windows(title):
        return True
    if restore_windows(title):
        time.sleep(1.5)
        if list_windows(title):
            return True

    exe = cfg.get("duong_dan_imou", "")
    if not cfg.get("tu_mo_imou", True):
        return False
    if not exe or not os.path.exists(exe):
        noi(u"Không thấy file chạy của Imou: %s" % exe)
        return False

    noi(u"App Imou chưa chạy – đang tự mở…")
    try:
        subprocess.Popen([exe], cwd=os.path.dirname(exe),
                         creationflags=0x00000008)          # DETACHED_PROCESS
    except Exception as e:
        noi(u"Không mở được app Imou: %s" % e)
        return False

    return cho_imou_san_sang(cfg, noi)


def giao_dien_da_len(img):
    """Cua so hien ra co phai GIAO DIEN CHINH khong (khong phai man hinh chao).

    Kiem tra bang cach doc chu o goc tren trai: giao dien chinh luon co hai the
    "Trang chu" va "Xem Lai".
    """
    if img is None or img.shape[1] < 900 or img.shape[0] < 600:
        return False
    try:
        from . import ocr
        lines = ocr.read(img[0:95, 0:420], scale=2.0)
        return (ocr.find_line(lines, u"trang", u"chu") is not None
                or ocr.find_line(lines, u"xem", u"lai") is not None)
    except Exception:
        return float(img.std()) >= 15.0        # khong doc duoc chu thi doan theo anh


def cho_imou_san_sang(cfg, noi=None):
    """Cho den khi giao dien chinh cua Imou hien ra."""
    noi = noi or (lambda *_a: None)
    title = cfg.get("window_title", "Imou")
    tong = float(cfg.get("cho_imou_giay", 90))
    bat_dau = time.time()
    while time.time() - bat_dau < tong:
        restore_windows(title)
        for hwnd in list_windows(title):
            if giao_dien_da_len(print_window(hwnd)):
                noi(u"App Imou đã sẵn sàng sau %d giây." % int(time.time() - bat_dau))
                time.sleep(2.0)                # cho giao dien on dinh han
                return True
        time.sleep(2.5)
    noi(u"Chờ quá %d giây mà giao diện Imou chưa hiện ra." % int(tong))
    return False


def find_window(title_part):
    wins = list_windows(title_part)
    return wins[0] if wins else None


def _longest_run(vec, threshold):
    """Doan lien tuc dai nhat co gia tri <= threshold."""
    idx = np.where(vec <= threshold)[0]
    if len(idx) < 10:
        return None
    parts = np.split(idx, np.where(np.diff(idx) > 3)[0] + 1)
    seg = max(parts, key=len)
    return int(seg[0]), int(seg[-1])


def detect_video_rect(img, margin=2):
    """Do tim vung khung hinh video trong anh cua so (tra ve ty le l,t,r,b).

    Khung giao dien Imou gan nhu trang/xam sang; vung video thi khong.
    Quet ty le diem anh "giao dien" theo tung cot roi tung hang de tim bien.
    """
    h, w = img.shape[:2]
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    ui = ((hsv[:, :, 1] < 40) & (hsv[:, :, 2] > 195)).astype(np.float32)

    cols = _longest_run(ui.mean(axis=0), 0.5)
    if cols is None:
        return None
    x1, x2 = cols
    if (x2 - x1) < w * 0.35:
        return None

    rows = _longest_run(ui[:, x1:x2 + 1].mean(axis=1), 0.5)
    if rows is None:
        return None
    y1, y2 = rows
    if (y2 - y1) < h * 0.35:
        return None

    x1, y1 = x1 + margin, y1 + margin
    x2, y2 = x2 - margin, y2 - margin
    return {
        "left": round(x1 / float(w), 4), "top": round(y1 / float(h), 4),
        "right": round((x2 + 1) / float(w), 4), "bottom": round((y2 + 1) / float(h), 4),
    }


class WindowCapture(object):
    """Nguon anh: vung ROI trong cua so Imou."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.hwnd = None
        self.mode = None            # "printwindow" | "manhinh"
        self._sct = None
        self.last_error = ""

    # ---------- gan cua so ----------
    def attach(self):
        """Chon cua so va che do chup tot nhat. True neu san sang."""
        wins = list_windows(self.cfg["window_title"])
        if not wins and restore_windows(self.cfg["window_title"]):
            time.sleep(1.2)                      # cho cua so hien lai
            wins = list_windows(self.cfg["window_title"])
        if not wins and self.cfg.get("tu_mo_imou", True):
            mo_app_imou(self.cfg, log=print)     # app bi tat -> tu mo lai
            wins = list_windows(self.cfg["window_title"])
        if not wins:
            self.hwnd, self.mode = None, None
            self.last_error = (
                u"Không tìm thấy cửa sổ '%s'. Hãy mở app Imou và xem camera."
                % self.cfg["window_title"]
            )
            return False

        want = self.cfg.get("capture_mode", "auto")
        best, best_score = None, -1.0
        if want in ("auto", "printwindow"):
            for hwnd in wins:
                img = print_window(hwnd)
                if img is None:
                    continue
                # cua so tra ve anh den hoan toan (khong ve duoc) -> std ~ 0.
                # Dung ca anh chu khong rieng vung video: video co the dang toi
                # (ban dem, dang tai) nhung khung giao dien thi luon co chi tiet.
                score = float(img.std())
                if score > best_score:
                    best, best_score = hwnd, score
            if best is not None and best_score >= 5.0:
                self.hwnd, self.mode = best, "printwindow"
                self.last_error = ""
                return True

        if want == "printwindow":
            self.hwnd, self.mode = None, None
            self.last_error = u"PrintWindow không lấy được hình từ cửa sổ Imou."
            return False

        self.hwnd, self.mode = wins[0], "manhinh"
        if self._sct is None:
            self._sct = mss.mss()
        self.last_error = ""
        return True

    def ready(self):
        return self.hwnd is not None and win32gui.IsWindow(self.hwnd)

    def window_rect(self):
        if not self.ready():
            return None
        try:
            return win32gui.GetWindowRect(self.hwnd)
        except Exception:
            return None

    def roi_box(self, w, h):
        """ROI theo pixel trong anh cua so (x1, y1, x2, y2)."""
        roi = self.cfg["roi"]
        x1 = max(0, int(round(w * roi["left"])))
        y1 = max(0, int(round(h * roi["top"])))
        x2 = min(w, int(round(w * roi["right"])))
        y2 = min(h, int(round(h * roi["bottom"])))
        if x2 - x1 < 40 or y2 - y1 < 40:
            return None
        return (x1, y1, x2, y2)

    def bring_to_front(self):
        if self.hwnd is None:
            return
        try:
            win32gui.ShowWindow(self.hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            pass

    def is_occluded(self):
        """Chi co y nghia o che do chup man hinh."""
        rect = self.window_rect()
        if rect is None:
            return True
        l, t, r, b = rect
        box = self.roi_box(r - l, b - t)
        if box is None:
            return True
        x1, y1, x2, y2 = box[0] + l, box[1] + t, box[2] + l, box[3] + t
        pts = [((x1 + x2) // 2, (y1 + y2) // 2), (x1 + 8, y1 + 8), (x2 - 8, y1 + 8),
               (x1 + 8, y2 - 8), (x2 - 8, y2 - 8)]
        try:
            own_pid = win32process.GetWindowThreadProcessId(self.hwnd)[1]
        except Exception:
            return True
        for px, py in pts:
            try:
                top = win32gui.WindowFromPoint((px, py))
                pid = win32process.GetWindowThreadProcessId(top)[1] if top else None
            except Exception:
                return True
            if pid != own_pid:
                return True
        return False

    # ---------- chup ----------
    def grab_full(self):
        """Chup toan bo cua so Imou. Tra ve (anh, loi)."""
        if not self.ready():
            if not self.attach():
                return None, self.last_error

        if self.mode == "printwindow":
            img = print_window(self.hwnd)
            if img is None:
                self.attach()
                return None, u"PrintWindow không trả về hình – đang thử lại."
            return img, ""

        # --- che do chup man hinh ---
        if win32gui.IsIconic(self.hwnd):
            if self.cfg.get("auto_focus_window"):
                self.bring_to_front()
            else:
                return None, u"Cửa sổ Imou đang thu nhỏ."
        if self.cfg.get("skip_when_occluded", True) and self.is_occluded():
            if self.cfg.get("auto_focus_window"):
                self.bring_to_front()
            if self.is_occluded():
                return None, u"Cửa sổ Imou bị che khuất – bỏ qua khung hình."

        rect = self.window_rect()
        if rect is None:
            return None, u"Không lấy được vị trí cửa sổ Imou."
        l, t, r, b = rect
        if self._sct is None:
            self._sct = mss.mss()
        try:
            raw = self._sct.grab({"left": l, "top": t, "width": r - l, "height": b - t})
        except Exception as e:
            return None, u"Lỗi chụp màn hình: %s" % e
        return cv2.cvtColor(np.array(raw), cv2.COLOR_BGRA2BGR), ""

    def grab(self):
        """Chup rieng vung ROI. Tra ve (anh, loi)."""
        img, err = self.grab_full()
        if img is None:
            return None, err
        h, w = img.shape[:2]
        box = self.roi_box(w, h)
        if box is None:
            return None, u"Vùng chụp không hợp lệ – hãy chọn lại vùng chụp."
        x1, y1, x2, y2 = box
        return img[y1:y2, x1:x2].copy(), ""

    def close(self):
        if self._sct is not None:
            try:
                self._sct.close()
            except Exception:
                pass
            self._sct = None
