# -*- coding: utf-8 -*-
"""Cac tac vu chay dai, dung chung cho ca dong lenh lan giao dien.

Moi ham deu nhan `log` de bao tien do ra ngoai, va co the bi dung giua chung
bang `app.huy.yeu_cau_dung()`.
"""
from datetime import datetime

from . import config, huy, imou_events, report, storage


def _ngay(ngay_str):
    return imou_events.ngay_tu_chuoi(ngay_str)


def quet_su_kien(ngay_str="", anh_net=True, log=print):
    """Doc su kien 'phat hien phuong tien' cua camera, kem chup lai anh net.

    Tra ve dict: {'ngay', 'so_luot', 'so_bo', 'bao_cao'}.
    """
    huy.xoa_yeu_cau()
    cfg = config.load()
    ngay = _ngay(ngay_str)
    log(u"Camera: %s | ngày %s" % (cfg.get("camera_name", ""),
                                   ngay.strftime("%d-%m-%Y")))

    events = imou_events.thu_thap(cfg, ngay=ngay, log=log)
    if not events:
        log(u"Không thấy sự kiện phương tiện nào trong ngày này.")
        return {"ngay": ngay, "so_luot": 0, "so_bo": 0, "bao_cao": None}

    if anh_net:
        from . import clip_capture
        log(u"Chụp lại ảnh nét từ clip ghi hình (%d sự kiện)…" % len(events))
        try:
            clip_capture.chup_anh_net(cfg, events, log=log)
        except huy.DaDung:
            raise
        except Exception as e:
            log(u"(!) Không chụp được ảnh nét: %s" % e)

    bo = [e for e in events if e.get("bo_qua")]
    if bo:
        log(u"Bỏ %d lượt không đúng hướng cần theo dõi." % len(bo))
        events = [e for e in events if not e.get("bo_qua")]

    _luu(cfg, ngay, events, log)
    web, _ = report.sinh_bao_cao(log=log)
    return {"ngay": ngay, "so_luot": len(events), "so_bo": len(bo), "bao_cao": web}


def duyet_clip(ngay_str="", log=print):
    """Duyet lan luot cac clip bang nut '>' trong cua so phat."""
    huy.xoa_yeu_cau()
    from . import duyet_clip as dc

    cfg = config.load()
    ngay = _ngay(ngay_str)
    log(u"Camera: %s | duyệt clip ngày %s"
        % (cfg.get("camera_name", ""), ngay.strftime("%d-%m-%Y")))

    events = dc.duyet(cfg, ngay, log=log)
    if not events:
        log(u"Không ghi nhận lượt xe nào.")
        return {"ngay": ngay, "so_luot": 0, "so_bo": 0, "bao_cao": None}

    events.sort(key=lambda e: e["thoi_gian"])
    _luu(cfg, ngay, events, log)
    web, _ = report.sinh_bao_cao(log=log)
    return {"ngay": ngay, "so_luot": len(events), "so_bo": 0, "bao_cao": web}


def _luu(cfg, ngay, events, log):
    """Ghi cac su kien ra thu muc phien cua ngay."""
    sid = "SUKIEN-" + ngay.strftime("%Y%m%d")
    sess = storage.Session(cfg, session_id=sid)
    sess.meta["nguon"] = u"Sự kiện phát hiện phương tiện của camera Imou"
    if events:
        sess.meta["bat_dau"] = events[0]["thoi_gian"]
        sess.meta["ket_thuc"] = events[-1]["thoi_gian"]
    for e in sorted(events, key=lambda x: x["thoi_gian"]):
        nhan = e.get("loai_xe_net")
        ev = sess.add_camera_event(
            e["thoi_gian"],
            e.get("anh_net") if e.get("anh_net") is not None else e.get("anh"),
            loai_xe=nhan or "vehicle",
            loai_xe_vi=cfg["classes_vi"].get(nhan, u"Phương tiện"),
            chac_chan=e.get("chac_chan", True),
            khung=e.get("khung_xe"), do_tin_cay=e.get("tin_cay"))
        log(u"  + %s  %s" % (ev["thoi_gian"], ev["anh"]))
    sess._flush()


def day_len_github(log=print):
    """Don bot ngay cu roi day len GitHub."""
    import subprocess

    from . import git_sync
    git_sync.don_dep(log=log)
    for lenh in (["git", "add", "-A"],
                 ["git", "commit", "-m",
                  "Cap nhat bao cao " + datetime.now().strftime("%d-%m-%Y %H:%M")],
                 ["git", "push"]):
        r = subprocess.run(lenh, cwd=storage.ROOT, capture_output=True,
                           text=True, encoding="utf-8", errors="replace")
        ra = (r.stdout or "") + (r.stderr or "")
        for dong in ra.splitlines()[:4]:
            if dong.strip():
                log(u"  " + dong.strip())
    log(u"Đã đẩy lên GitHub.")
