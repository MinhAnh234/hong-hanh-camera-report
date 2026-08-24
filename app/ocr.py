# -*- coding: utf-8 -*-
"""Doc chu tren anh bang bo OCR co san cua Windows (Windows.Media.Ocr).

Khong can cai them phan mem ngoai, chay hoan toan ngoai tuyen.
"""
import asyncio
import re
import unicodedata

import cv2
import numpy as np

_ENGINE = None
_LOOP = None


class Word(object):
    __slots__ = ("text", "box")

    def __init__(self, text, box):
        self.text = text
        self.box = box          # (x, y, w, h)

    @property
    def center(self):
        x, y, w, h = self.box
        return (x + w // 2, y + h // 2)

    def __repr__(self):
        return "Word(%r, %s)" % (self.text, self.box)


class Line(object):
    __slots__ = ("text", "box", "words")

    def __init__(self, text, box, words):
        self.text = text
        self.box = box
        self.words = words

    @property
    def center(self):
        x, y, w, h = self.box
        return (x + w // 2, y + h // 2)

    def __repr__(self):
        return "Line(%r, %s)" % (self.text, self.box)


def _engine():
    global _ENGINE
    if _ENGINE is None:
        from winsdk.windows.globalization import Language
        from winsdk.windows.media.ocr import OcrEngine

        # Bo OCR theo ngon ngu he thong doc so gio chinh xac hon en-US
        # (en-US hay bo mat phan gio trong chuoi "2026/08/23 16:37:10").
        eng = OcrEngine.try_create_from_user_profile_languages()
        for tag in () if eng is not None else ("en-US", "vi-VN"):
            try:
                if OcrEngine.is_language_supported(Language(tag)):
                    eng = OcrEngine.try_create_from_language(Language(tag))
                    if eng is not None:
                        break
            except Exception:
                pass
        if eng is None:
            raise RuntimeError(
                u"Máy chưa bật gói OCR của Windows. "
                u"Vào Settings > Time & language > Language & region để thêm gói ngôn ngữ."
            )
        _ENGINE = eng
    return _ENGINE


def _loop():
    global _LOOP
    if _LOOP is None:
        _LOOP = asyncio.new_event_loop()
    return _LOOP


def _to_bitmap(bgr):
    from winsdk.windows.graphics.imaging import BitmapPixelFormat, SoftwareBitmap
    from winsdk.windows.storage.streams import DataWriter

    bgra = cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    h, w = bgra.shape[:2]
    writer = DataWriter()
    writer.write_bytes(bgra.tobytes())
    buf = writer.detach_buffer()
    return SoftwareBitmap.create_copy_from_buffer(buf, BitmapPixelFormat.BGRA8, w, h)


def read(bgr, scale=1.0):
    """Doc chu tren anh BGR. Tra ve danh sach Line (toa do theo anh goc)."""
    if bgr is None or bgr.size == 0:
        return []
    if scale != 1.0:
        bgr = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    engine = _engine()
    bitmap = _to_bitmap(bgr)

    async def go():
        return await engine.recognize_async(bitmap)

    result = _loop().run_until_complete(go())

    lines = []
    for ln in result.lines:
        words = []
        for wd in ln.words:
            r = wd.bounding_rect
            words.append(Word(wd.text, (int(r.x / scale), int(r.y / scale),
                                        int(r.width / scale), int(r.height / scale))))
        if not words:
            continue
        x1 = min(w.box[0] for w in words)
        y1 = min(w.box[1] for w in words)
        x2 = max(w.box[0] + w.box[2] for w in words)
        y2 = max(w.box[1] + w.box[3] for w in words)
        lines.append(Line(ln.text, (x1, y1, x2 - x1, y2 - y1), words))
    return lines


def read_text(bgr, scale=1.0):
    return u"\n".join(l.text for l in read(bgr, scale))


def fold(s):
    """Bo dau, bo khoang trang, ve chu thuong -> de so khop du OCR doc sai dau.

    Bo OCR cua Windows khong co goi tieng Viet nen dau thuong bi doc lech
    ("Lam Moi" -> "Lam Mdi"). So khop tren chuoi da bo dau on dinh hon nhieu.
    """
    s = unicodedata.normalize("NFD", s or u"")
    s = u"".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.replace(u"đ", u"d").replace(u"Đ", u"d")
    return u"".join(c for c in s.lower() if c.isalnum())


def find_line(lines, *keywords):
    """Dong dau tien chua tat ca tu khoa (da bo dau, bo khoang trang)."""
    keys = [fold(k) for k in keywords if fold(k)]
    for ln in lines:
        flat = fold(ln.text)
        if all(k in flat for k in keys):
            return ln
    return None


def find_lines(lines, *keywords):
    keys = [fold(k) for k in keywords if fold(k)]
    return [ln for ln in lines if all(k in fold(ln.text) for k in keys)]


_TS_RE = re.compile(r"(\d{4})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})\D{0,4}"
                    r"(\d{1,2})\D{0,3}(\d{1,2})\D{0,3}(\d{1,2})")


def parse_timestamp(text):
    """Doc chuoi kieu '2026 / 08 / 23 1 6 : 37 : 10' -> '2026-08-23 16:37:10'."""
    digits = re.sub(r"[^\d]", "", text or "")
    if len(digits) == 14:
        y, mo, d = digits[0:4], digits[4:6], digits[6:8]
        hh, mi, ss = digits[8:10], digits[10:12], digits[12:14]
    else:
        m = _TS_RE.search(text or "")
        if not m:
            return None
        y, mo, d, hh, mi, ss = m.groups()
    try:
        y, mo, d, hh, mi, ss = int(y), int(mo), int(d), int(hh), int(mi), int(ss)
    except ValueError:
        return None
    if not (2000 <= y <= 2100 and 1 <= mo <= 12 and 1 <= d <= 31
            and hh <= 23 and mi <= 59 and ss <= 59):
        return None
    return "%04d-%02d-%02d %02d:%02d:%02d" % (y, mo, d, hh, mi, ss)
