# -*- coding: utf-8 -*-
"""Co hieu "dung lai" dung chung cho cac tac vu chay lau.

Cac vong lap dai (quet su kien, duyet clip, chup anh) goi `kiem_tra()` o dau moi
vong; khi nguoi dung bam DUNG thi ham nay nem ra `DaDung` de thoat ngay, thay vi
phai cho het viec.
"""
import threading

_co = threading.Event()


class DaDung(Exception):
    """Nguoi dung yeu cau dung giua chung."""


def yeu_cau_dung():
    _co.set()


def xoa_yeu_cau():
    _co.clear()


def can_dung():
    return _co.is_set()


def kiem_tra():
    """Nem DaDung neu nguoi dung da bam dung."""
    if _co.is_set():
        raise DaDung()
