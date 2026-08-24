# -*- coding: utf-8 -*-
"""Doc day so "YYYY/MM/DD HH:MM:SS" bang doi sanh mau (template matching).

Vi sao can: chu tren the su kien cua Imou chi cao ~9 diem anh, bo OCR cua
Windows hay lan lon 5 va 6. Nhung moi ky tu deu duoc ve bang CUNG mot font,
CUNG mot co, nen so sanh truc tiep hinh dang cho ket qua chinh xac.

Cach lam:
  1. Tach tung ky tu (thanh phan lien thong) tren dai chu.
  2. Chuoi luon co dang 4 so / 2 so / 2 so - 2 so : 2 so : 2 so  => 16 o,
     trong do o thu 5 va thu 8 la dau "/".
  3. 8 chu so dau chinh la NGAY dang chon (da biet chac) -> lay lam mau.
  4. Cac chu so con lai doi chieu voi kho mau; chua co mau thi tin OCR va
     bo sung mau moi.
"""
import cv2
import numpy as np

PATCH = (14, 18)          # (rong, cao) chuan hoa moi ky tu


def _norm(patch):
    p = cv2.resize(patch.astype(np.float32), PATCH, interpolation=cv2.INTER_AREA)
    p -= p.mean()
    n = np.linalg.norm(p)
    return p / n if n > 1e-6 else p


def extract_chars(strip_bgr, dark_max=195):
    """Tach cac ky tu 'cao' (chu so va dau /) tren dai chu -> [(x, anh_nhi_phan)]."""
    if strip_bgr is None or strip_bgr.size == 0:
        return []
    gray = cv2.cvtColor(strip_bgr, cv2.COLOR_BGR2GRAY)
    binary = (gray < dark_max).astype(np.uint8)
    n, _lab, stats, _cent = cv2.connectedComponentsWithStats(binary, 8)
    boxes = []
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        if area < 3 or w < 1 or h < 3:
            continue
        boxes.append((x, y, w, h))
    if not boxes:
        return []
    cao_nhat = max(b[3] for b in boxes)
    chars = []
    for x, y, w, h in boxes:
        if h < cao_nhat * 0.6:            # bo dau hai cham (cham nho)
            continue
        chars.append((x, binary[y:y + h, x:x + w] * 255))
    chars.sort(key=lambda t: t[0])
    return _tach_ky_tu_dinh_nhau(chars)


def _tach_ky_tu_dinh_nhau(chars):
    """Hai ky tu ve dinh nhau se thanh mot khoi rong gap doi -> cat lam doi."""
    if len(chars) < 4:
        return chars
    # Be rong chuan cua MOT chu so: lay trung vi cac khoi co be rong "kieu chu so"
    # (bo qua dau "/" va so 1 vi chung rat hep).
    rong = sorted(c.shape[1] for _x, c in chars if 4 <= c.shape[1] <= 9)
    if not rong:
        rong = sorted(c.shape[1] for _x, c in chars)
    chuan = rong[len(rong) // 2]
    if chuan < 2:
        return chars
    out = []
    for x, c in chars:
        phan = int(c.shape[1] / float(chuan) + 0.35)
        if phan <= 1 or c.shape[1] < chuan * 1.55:
            out.append((x, c))
            continue
        # Cat tai cot co IT DIEM ANH NHAT quanh vi tri chia deu -> dung net hon
        muc = (c > 0).sum(axis=0)
        buoc = c.shape[1] / float(phan)
        moc = [0]
        for i in range(1, phan):
            uoc = int(round(i * buoc))
            lo, hi = max(1, uoc - 2), min(c.shape[1] - 1, uoc + 3)
            if hi > lo:
                uoc = lo + int(np.argmin(muc[lo:hi]))
            moc.append(uoc)
        moc.append(c.shape[1])
        for i in range(phan):
            a, b = moc[i], moc[i + 1]
            if b - a >= 1:
                out.append((x + a, c[:, a:b]))
    out.sort(key=lambda t: t[0])
    return out


class DigitReader(object):
    """Kho mau chu so, tu hoc dan trong qua trinh doc."""

    def __init__(self):
        self.mau = {}                     # ky tu -> [vector mau]

    def them(self, patch, label):
        v = _norm(patch)
        kho = self.mau.setdefault(label, [])
        for cu in kho:
            if float((cu * v).sum()) > 0.985:      # da co mau gan giong
                return
        if len(kho) < 6:
            kho.append(v)

    def doan(self, patch):
        """-> (ky_tu, diem_giong) ; diem_giong trong khoang -1..1."""
        if not self.mau:
            return None, 0.0
        v = _norm(patch)
        tot, diem = None, -1.0
        for label, kho in self.mau.items():
            for m in kho:
                d = float((m * v).sum())
                if d > diem:
                    tot, diem = label, d
        return tot, diem

    # ---------- doc ca day ----------
    def doc_day(self, strip_bgr, ngay_biet=None, goi_y=None):
        """Doc dai chu thoi gian.

        ngay_biet: 8 chu so cua NGAY da biet chac (vd '20260823') -> dung lam mau.
        goi_y:     14 chu so OCR doc duoc (neu co) -> bo sung mau va do phong.

        Tra ve (chuoi_14_chu_so, diem_giong_thap_nhat) hoac (None, 0.0).
        """
        chars = extract_chars(strip_bgr)
        if len(chars) != 16:              # 14 chu so + 2 dau "/"
            return None, 0.0
        so = [p for i, (_x, p) in enumerate(chars) if i not in (4, 7)]
        if len(so) != 14:
            return None, 0.0

        if ngay_biet and len(ngay_biet) == 8:
            for p, ch in zip(so[:8], ngay_biet):
                self.them(p, ch)
        if goi_y and len(goi_y) == 14:
            for p, ch in zip(so, goi_y):
                self.them(p, ch)

        ket_qua, thap_nhat = [], 1.0
        for i, p in enumerate(so):
            if ngay_biet and i < 8:
                ket_qua.append(ngay_biet[i])
                continue
            ch, diem = self.doan(p)
            if ch is None:
                return None, 0.0
            ket_qua.append(ch)
            thap_nhat = min(thap_nhat, diem)
        return "".join(ket_qua), thap_nhat
