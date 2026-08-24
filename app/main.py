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
    from . import imou_events

    cfg = config.load()
    ngay = imou_events.ngay_tu_chuoi(ngay_str)
    print(u"Camera: %s | ngày %s" % (cfg.get("camera_name", ""), ngay.strftime("%d-%m-%Y")))

    events = imou_events.thu_thap(cfg, ngay=ngay)
    if not events:
        print(u"Không thấy sự kiện phương tiện nào trong ngày này.")
        return 1

    if anh_net:
        from . import clip_capture
        print(u"Chụp lại ảnh nét từ clip ghi hình (%d sự kiện)…" % len(events))
        try:
            so = clip_capture.chup_anh_net(cfg, events)
            print(u"Đã chụp nét %d/%d sự kiện." % (so, len(events)))
        except Exception as e:
            print(u"(!) Không chụp được ảnh nét: %s" % e)

    bo = [e for e in events if e.get("bo_qua")]
    if bo:
        print(u"Bỏ qua %d lượt không đúng hướng cần theo dõi:" % len(bo))
        for e in bo:
            print(u"   - %s (%s)" % (e["thoi_gian"][11:], e["bo_qua"]))
        events = [e for e in events if not e.get("bo_qua")]
    if not events:
        print(u"Không còn lượt nào sau khi lọc theo hướng.")
        return 1

    sid = "SUKIEN-" + ngay.strftime("%Y%m%d")
    sess = storage.Session(cfg, session_id=sid)
    sess.meta["nguon"] = u"Sự kiện phát hiện phương tiện của camera Imou"
    sess.meta["bat_dau"] = events[0]["thoi_gian"]
    sess.meta["ket_thuc"] = events[-1]["thoi_gian"]
    for e in events:
        nhan = e.get("loai_xe_net")
        ev = sess.add_camera_event(
            e["thoi_gian"], e.get("anh_net") if e.get("anh_net") is not None else e["anh"],
            loai_xe=nhan or "vehicle",
            loai_xe_vi=cfg["classes_vi"].get(nhan, u"Phương tiện"),
            chac_chan=e.get("chac_chan", True),
            khung=e.get("khung_xe"), do_tin_cay=e.get("tin_cay"))
        print(u"  + %s%s  %s" % (ev["thoi_gian"],
                                 u"" if ev["thoi_gian_chac_chan"] else u"  (≈)",
                                 ev["anh"]))
    sess._flush()

    print(u"Tổng cộng %d lượt xe %s."
          % (len(events),
             {"trai_sang_phai": u"đi trái → phải (ra khỏi mỏ)",
              "phai_sang_trai": u"đi phải → trái"}.get(
                  cfg.get("huong_xe", "ca_hai"), u"(mọi hướng)")))
    web, _day_du = report.sinh_bao_cao(log=print)
    if open_report:
        try:
            os.startfile(web)
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

    if args.su_kien:
        return _doc_su_kien_camera(args.ngay, not args.khong_mo, not args.khong_anh_net)

    if args.nen:
        return _run_headless(args.phut, not args.khong_mo)

    from .gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    sys.exit(main())
