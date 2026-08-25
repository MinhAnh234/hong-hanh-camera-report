# -*- coding: utf-8 -*-
"""Diem chay chinh.

  python -m app.main                 -> mo giao dien
  python -m app.main --nen --phut 30 -> chay nen 30 phut roi tu xuat bao cao
  python -m app.main --bao-cao <ma>  -> xuat lai bao cao cua mot phien
  python -m app.main --danh-sach     -> liet ke cac phien da co
"""
import argparse
import os
import sys
import time

from . import config, report, storage


def _run_headless(minutes, open_report):
    from .engine import MonitorEngine

    cfg = config.load()
    engine = MonitorEngine(
        cfg,
        on_event=lambda ev, tr: print(
            u"  [+] %s  %-16s tin cay %.0f%%  -> %s"
            % (ev["thoi_gian"][11:], ev["loai_xe_vi"], ev["do_tin_cay"] * 100, ev["anh"])
        ),
    )
    session = engine.start()
    print(u"Phien: %s" % session.session_id)
    print(u"Camera: %s" % cfg.get("camera_name", ""))
    print(u"Thu muc anh: %s" % session.dir)
    if minutes:
        print(u"Se chay %g phut. Nhan Ctrl+C de dung som." % minutes)
    else:
        print(u"Dang chay. Nhan Ctrl+C de dung.")

    deadline = time.time() + minutes * 60 if minutes else None
    try:
        while engine.running:
            time.sleep(1.0)
            if deadline and time.time() >= deadline:
                break
    except KeyboardInterrupt:
        print(u"\nDang dung...")
    engine.stop()

    st = engine.stats
    print(u"Ket thuc: %d khung hinh, %d lan chuyen dong, %d luot xe."
          % (st["khung_hinh"], st["lan_chuyen_dong"], st["su_kien"]))
    path = report.build(session.session_id)
    report.sinh_bao_cao()
    print(u"Bao cao: %s" % path)
    if open_report:
        try:
            os.startfile(path)
        except Exception:
            pass
    return 0


def _doc_su_kien_camera(ngay_str, open_report, anh_net=True):
    """Doc su kien 'phat hien phuong tien' ma camera Imou da tu ghi lai."""
    from . import chay

    kq = chay.quet_su_kien(ngay_str, anh_net=anh_net, log=print)
    if not kq["so_luot"]:
        return 1
    print(u"Tổng cộng %d lượt xe ra khỏi mỏ." % kq["so_luot"])
    if open_report and kq["bao_cao"]:
        try:
            os.startfile(kq["bao_cao"])
        except Exception:
            pass
    return 0


def _duyet_clip(ngay_str, open_report):
    """Duyet lan luot tung clip bang nut '>' trong cua so phat."""
    from . import chay

    kq = chay.duyet_clip(ngay_str, log=print)
    if not kq["so_luot"]:
        return 1
    print(u"Tổng cộng %d lượt xe ra khỏi mỏ." % kq["so_luot"])
    if open_report and kq["bao_cao"]:
        try:
            os.startfile(kq["bao_cao"])
        except Exception:
            pass
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description=u"App chup anh xe va bao cao HTML")
    p.add_argument("--nen", "--headless", action="store_true", dest="nen",
                   help=u"chay khong giao dien")
    p.add_argument("--phut", type=float, default=0,
                   help=u"so phut chay o che do nen (0 = chay den khi Ctrl+C)")
    p.add_argument("--bao-cao", dest="bao_cao", metavar="MA_PHIEN",
                   help=u"xuat lai bao cao HTML cua mot phien")
    p.add_argument("--su-kien", action="store_true", dest="su_kien",
                   help=u"doc su kien phat hien phuong tien san co cua camera Imou")
    p.add_argument("--ngay", default="",
                   help=u"ngay can lay: 23 | 23-08 | 2026-08-23 | hom-nay | hom-qua")
    p.add_argument("--khong-anh-net", action="store_true", dest="khong_anh_net",
                   help=u"bo qua buoc mo clip de chup anh net (nhanh hon, anh mo)")
    p.add_argument("--duyet-clip", action="store_true", dest="duyet_clip",
                   help=u"duyet lan luot tung clip bang nut '>' trong cua so phat")
    p.add_argument("--trang-chu", action="store_true", dest="trang_chu",
                   help=u"sinh lai bao cao gop (index.html + ban day du)")
    p.add_argument("--danh-sach", action="store_true", help=u"liet ke cac phien da co")
    p.add_argument("--khong-mo", action="store_true", help=u"khong tu mo file bao cao")
    args = p.parse_args(argv)

    if args.danh_sach:
        sessions = storage.list_sessions()
        if not sessions:
            print(u"Chua co phien nao.")
        for s in sessions:
            data = storage.load_session(s)
            print(u"%-28s %3d luot  %s"
                  % (s, len(data.get("su_kien", [])), data["phien"].get("bat_dau", "")))
        return 0

    if args.trang_chu:
        report.sinh_bao_cao(log=print)
        return 0

    if args.bao_cao:
        path = report.build(args.bao_cao)
        report.sinh_bao_cao()
        print(u"Bao cao: %s" % path)
        if not args.khong_mo:
            try:
                os.startfile(path)
            except Exception:
                pass
        return 0

    if args.duyet_clip:
        return _duyet_clip(args.ngay, not args.khong_mo)

    if args.su_kien:
        return _doc_su_kien_camera(args.ngay, not args.khong_mo, not args.khong_anh_net)

    if args.nen:
        return _run_headless(args.phut, not args.khong_mo)

    from .gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
