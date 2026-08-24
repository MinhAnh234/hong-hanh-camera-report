# -*- coding: utf-8 -*-
"""Giu dung lieu tren GitHub gon nhe: chi day len N NGAY GAN NHAT.

O MAY thi van giu day du - khong xoa file nao ca. Chi go cac phien cu ra khoi
danh sach theo doi cua git (git rm --cached) va ghi vao .git/info/exclude de
lan sau `git add -A` khong them lai.
"""
import os
import re
import subprocess

from . import storage

ROOT = storage.ROOT
NGAY_MAC_DINH = 3
_MOC = "# --- app tu quan ly: phien cu khong day len GitHub ---"
_NGAY = re.compile(r"(\d{8})")


def _git(*args):
    return subprocess.run(["git"] + list(args), cwd=ROOT,
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace")


def _ngay_cua_phien(sid):
    """Lay ngay (YYYYMMDD) tu ma phien, vd SUKIEN-20260824 / PHIEN-20260823-233751."""
    m = _NGAY.search(sid)
    return m.group(1) if m else ""


def phien_theo_ngay():
    """{ngay: [ma phien]} sap xep ngay moi truoc."""
    theo = {}
    for sid in storage.list_sessions():
        ngay = _ngay_cua_phien(sid)
        if ngay:
            theo.setdefault(ngay, []).append(sid)
    return theo


def _ghi_exclude(duong_dan):
    """Ghi danh sach thu muc khong theo doi vao .git/info/exclude (chi o may nay)."""
    f = os.path.join(ROOT, ".git", "info", "exclude")
    os.makedirs(os.path.dirname(f), exist_ok=True)
    cu = []
    if os.path.exists(f):
        with open(f, "r", encoding="utf-8") as fh:
            for dong in fh.read().splitlines():
                if dong.strip() == _MOC:
                    break
                cu.append(dong)
    with open(f, "w", encoding="utf-8") as fh:
        fh.write("\n".join(cu).rstrip("\n"))
        fh.write("\n%s\n" % _MOC)
        for d in sorted(duong_dan):
            fh.write("%s\n" % d)


def don_dep(giu=NGAY_MAC_DINH, log=None):
    """Chi de lai `giu` ngay gan nhat trong repo. Tra ve (so ngay giu, so ngay go)."""
    noi = log or (lambda *_a: None)
    theo = phien_theo_ngay()
    if not theo:
        return 0, 0

    ngay_sap = sorted(theo, reverse=True)
    ngay_giu, ngay_go = ngay_sap[:giu], ngay_sap[giu:]

    bo = []
    for ngay in ngay_go:
        for sid in theo[ngay]:
            bo.append("captures/%s/" % sid)
    _ghi_exclude(bo)

    for ngay in ngay_go:
        for sid in theo[ngay]:
            r = _git("rm", "-r", "--cached", "--ignore-unmatch", "-q",
                     "captures/%s" % sid)
            if r.returncode == 0:
                noi(u"  gỡ khỏi GitHub (vẫn giữ ở máy): %s" % sid)

    noi(u"Trên GitHub giữ %d ngày gần nhất: %s"
        % (len(ngay_giu), ", ".join(sorted(ngay_giu, reverse=True))))
    if ngay_go:
        noi(u"Đã gỡ %d ngày cũ khỏi GitHub (file vẫn còn trong thư mục captures)."
            % len(ngay_go))
    return len(ngay_giu), len(ngay_go)


if __name__ == "__main__":
    don_dep(log=print)
