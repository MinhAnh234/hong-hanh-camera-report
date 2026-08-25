# -*- coding: utf-8 -*-
"""Kiem tra va chuan bi moi truong chay tren mot may moi.

Chay:  python -m app.cai_dat          -> kiem tra + tai thu con thieu
       python -m app.cai_dat --kiem-tra -> chi kiem tra, khong tai gi
"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_DIR = os.path.join(ROOT, "models")

GOI = [
    ("cv2", "opencv-python==4.10.0.84",
     u"đọc/ghi ảnh, nhận dạng xe (bản 5.x KHÔNG dùng được)"),
    ("numpy", "numpy", u"tính toán ma trận ảnh"),
    ("mss", "mss", u"chụp màn hình"),
    ("win32gui", "pywin32", u"điều khiển cửa sổ Windows"),
    ("PIL", "pillow", u"vẽ chữ tiếng Việt lên ảnh"),
    ("winsdk", "winsdk", u"dùng bộ OCR có sẵn của Windows"),
]

MO_HINH = [
    ("yolov4-tiny.cfg", 3231,
     "https://raw.githubusercontent.com/AlexeyAB/darknet/master/cfg/yolov4-tiny.cfg"),
    ("coco.names", 625,
     "https://raw.githubusercontent.com/pjreddie/darknet/master/data/coco.names"),
    ("yolov4-tiny.weights", 24251276,
     "https://github.com/AlexeyAB/darknet/releases/download/darknet_yolo_v4_pre/"
     "yolov4-tiny.weights"),
]

NOI_CAI_IMOU = [
    r"C:\Program Files\Imou_en\bin\Imou_en.exe",
    r"C:\Program Files (x86)\Imou_en\bin\Imou_en.exe",
    r"C:\Program Files\Imou\bin\Imou.exe",
]

OK, LOI, CANH = u"  [OK] ", u"  [THIEU] ", u"  [LUU Y] "


def _in(dau, *phan):
    print(dau + u" ".join(str(p) for p in phan))


# ---------------------------------------------------------------- kiem tra
def kiem_tra_python():
    v = sys.version_info
    if v < (3, 8):
        _in(LOI, u"Python %d.%d quá cũ, cần Python 3.8 trở lên." % (v[0], v[1]))
        return False
    _in(OK, u"Python %d.%d.%d" % v[:3])
    return True


def kiem_tra_goi(tu_cai=True):
    thieu = []
    for ten_import, ten_pip, mo_ta in GOI:
        try:
            __import__(ten_import)
            _in(OK, u"%-14s %s" % (ten_pip.split("==")[0], mo_ta))
        except Exception:
            thieu.append((ten_pip, mo_ta))
            _in(LOI, u"%-14s %s" % (ten_pip.split("==")[0], mo_ta))

    if thieu and tu_cai:
        print(u"\n  Đang cài %d gói còn thiếu…" % len(thieu))
        r = subprocess.run([sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
                           + [g for g, _m in thieu])
        if r.returncode != 0:
            _in(LOI, u"Cài gói thất bại. Hãy chạy tay:")
            print(u"      %s -m pip install %s"
                  % (sys.executable, " ".join(g for g, _m in thieu)))
            return False
        return kiem_tra_goi(tu_cai=False)
    return not thieu


def kiem_tra_opencv():
    try:
        import cv2
    except Exception:
        return False
    ban = cv2.__version__
    if not hasattr(cv2.dnn, "readNetFromDarknet"):
        _in(LOI, u"OpenCV %s không nạp được mô hình Darknet. Hãy hạ về 4.10:" % ban)
        print(u'      %s -m pip install "opencv-python==4.10.0.84"' % sys.executable)
        return False
    _in(OK, u"OpenCV %s (nạp được mô hình YOLO)" % ban)
    return True


def kiem_tra_mo_hinh(tu_tai=True):
    os.makedirs(MODEL_DIR, exist_ok=True)
    thieu = []
    for ten, co_nho_nhat, url in MO_HINH:
        p = os.path.join(MODEL_DIR, ten)
        if os.path.exists(p) and os.path.getsize(p) >= co_nho_nhat * 0.9:
            _in(OK, u"models/%s (%.1f MB)" % (ten, os.path.getsize(p) / 1e6))
        else:
            thieu.append((ten, url))
            _in(LOI, u"models/%s" % ten)

    if thieu and tu_tai:
        import urllib.request
        for ten, url in thieu:
            print(u"  Đang tải %s…" % ten)
            try:
                urllib.request.urlretrieve(url, os.path.join(MODEL_DIR, ten))
            except Exception as e:
                _in(LOI, u"Tải %s thất bại: %s" % (ten, e))
                print(u"      Tải tay từ: %s" % url)
                print(u"      rồi bỏ vào thư mục: %s" % MODEL_DIR)
                return False
        return kiem_tra_mo_hinh(tu_tai=False)
    return not thieu


def kiem_tra_ocr():
    try:
        from . import ocr
        eng = ocr._engine()
        _in(OK, u"OCR của Windows (ngôn ngữ: %s)" % eng.recognizer_language.language_tag)
        return True
    except Exception as e:
        _in(LOI, u"Chưa dùng được OCR của Windows: %s" % e)
        print(u"      Vào Settings > Time & language > Language & region,")
        print(u"      chọn ngôn ngữ đang có > Language options > cài gói OCR.")
        return False


def kiem_tra_imou():
    from . import config
    cfg = config.load()
    duong = cfg.get("duong_dan_imou", "")
    if duong and os.path.exists(duong):
        _in(OK, u"App Imou: %s" % duong)
    else:
        tim = [p for p in NOI_CAI_IMOU if os.path.exists(p)]
        if tim:
            cfg["duong_dan_imou"] = tim[0]
            config.save(cfg)
            _in(OK, u"App Imou: %s (đã ghi vào config.json)" % tim[0])
        else:
            _in(LOI, u"Không thấy app Imou trên máy này.")
            print(u"      Cài Imou cho PC rồi sửa 'duong_dan_imou' trong config.json.")
            return False

    try:
        from .capture import list_windows
        so = len(list_windows(cfg.get("window_title", "Imou")))
        if so:
            _in(OK, u"Cửa sổ Imou đang mở (%d cửa sổ)" % so)
        else:
            _in(CANH, u"App Imou chưa mở – app sẽ tự mở khi cần.")
    except Exception:
        pass
    return True


def kiem_tra_cau_hinh():
    from . import config
    cfg = config.load()
    _in(OK, u"Camera trong cấu hình: %s" % cfg.get("camera_name", "?"))
    _in(OK, u"Hướng xe ghi nhận: %s" % (u"tất cả các hướng"
        if cfg.get("huong_xe", "ca_hai") == "ca_hai"
        else cfg.get("huong_xe")))
    print(u"      Nếu tên camera khác, sửa 'camera_name' trong config.json cho khớp")
    print(u"      với tên hiển thị trong app Imou.")
    return True


# ---------------------------------------------------------------- chay
def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    chi_kiem_tra = "--kiem-tra" in argv

    print(u"\n=== KIEM TRA MOI TRUONG ===\n")
    buoc = [
        (u"1. Python", lambda: kiem_tra_python()),
        (u"2. Thu vien", lambda: kiem_tra_goi(tu_cai=not chi_kiem_tra)),
        (u"3. OpenCV", lambda: kiem_tra_opencv()),
        (u"4. Mo hinh nhan dang", lambda: kiem_tra_mo_hinh(tu_tai=not chi_kiem_tra)),
        (u"5. OCR cua Windows", lambda: kiem_tra_ocr()),
        (u"6. App Imou", lambda: kiem_tra_imou()),
        (u"7. Cau hinh", lambda: kiem_tra_cau_hinh()),
    ]
    hong = []
    for ten, ham in buoc:
        print(ten)
        try:
            if not ham():
                hong.append(ten)
        except Exception as e:
            _in(LOI, u"lỗi: %s" % e)
            hong.append(ten)
        print()

    if hong:
        print(u"=== CHUA XONG: %s ===" % ", ".join(hong))
        print(u"Xem lai cac dong [THIEU] o tren.")
        return 1
    print(u"=== SAN SANG CHAY ===")
    print(u"  Buoc tiep theo:")
    print(u"   1. Mo app Imou, dang nhap, xem camera mot lan cho chac.")
    print(u"   2. Chay CHON_VUNG_CHUP.bat de app biet vung khung hinh video.")
    print(u"   3. Chay DOC_SU_KIEN_CAMERA.bat de lay bao cao ngay hom nay.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
