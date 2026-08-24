# -*- coding: utf-8 -*-
"""Cau hinh app: doc/ghi config.json, kem gia tri mac dinh."""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(ROOT, "config.json")

DEFAULTS = {
    # --- Cua so nguon ---
    "window_title": "Imou",           # tim cua so theo tieu de (khop mot phan)
    "camera_name": "AOV PT-BE5",      # ten camera ghi vao bao cao
    # "auto" = uu tien PrintWindow (chup duoc ca khi bi che), "manhinh" = chup man hinh
    "capture_mode": "auto",

    # --- Tu mo app Imou khi no chua chay (can cho lich chay tu dong) ---
    "tu_mo_imou": True,
    "duong_dan_imou": "C:\\Program Files\\Imou_en\\bin\\Imou_en.exe",
    "cho_imou_giay": 90,              # cho toi da bao nhieu giay de cua so hien ra

    # Vung chup (ty le so voi cua so Imou, 0..1). Mac dinh = vung khung hinh video.
    "roi": {"left": 0.1914, "top": 0.1134, "right": 0.9843, "bottom": 0.9106},

    # --- Vong lap chup ---
    "fps": 3.0,                       # so khung hinh xu ly moi giay
    "auto_focus_window": False,       # tu dua cua so Imou len truoc khi bi che
    "skip_when_occluded": True,       # bo qua khung hinh khi cua so bi che khuat

    # --- Phat hien chuyen dong ---
    "motion_min_area_ratio": 0.0006,  # (chi de thong ke) ty le dien tich chuyen dong
    "motion_min_region_side": 12,     # canh nho nhat cua vung chuyen dong dang xet
    "motion_var_threshold": 32,
    "motion_history": 300,
    # ty le diem anh chuyen dong toi thieu trong khung xe (0 = tat bo loc nay)
    "min_motion_in_box": 0.0,

    # --- Nhan dang phuong tien ---
    "conf_threshold": 0.30,
    "nms_threshold": 0.45,
    "input_size": 320,           # do phan giai o quet (nho = nhanh)
    # Camera dat xa -> chi quet o quanh vung chuyen dong roi phong to de phan loai
    "scan_window_min": 380,           # canh nho nhat cua o quet (diem anh)
    "scan_window_pad": 1.7,           # o quet rong gap may lan vung chuyen dong
    "scan_max_regions": 8,            # so o quet toi da moi khung hinh
    "refine_labels": True,            # quet lai o do phan giai cao de phan loai
    "refine_input_size": 608,
    "classes_vi": {
        "car": "Xe ô tô",
        "truck": "Xe ben / xe tải",
        "bus": "Xe khách",
        "motorbike": "Xe máy",
        "motorcycle": "Xe máy",
    },
    "watch_classes": ["car", "truck", "bus"],   # loai xe can bat su kien

    # --- Loc theo HUONG DI CHUYEN cua xe ---
    # "trai_sang_phai" = chi lay xe di tu trai qua phai (xe ra khoi mo)
    # "phai_sang_trai" = nguoc lai ; "ca_hai" = lay tat ca
    "huong_xe": "trai_sang_phai",
    "huong_min_dx": 25,               # so diem anh toi thieu theo truc ngang de ket luan
    "giu_khi_khong_ro_huong": True,   # van giu lai luot khong xac dinh duoc huong

    # --- Bam vet & luu su kien ---
    "track_min_hits": 2,              # so lan thay lien tiep truoc khi xac nhan
    "track_min_move_px": 5,          # quang duong toi thieu de coi la "dang chuyen dong"
    "track_max_missing": 30,          # so khung hinh mat dau vet truoc khi dong vet
    "event_cooldown_sec": 3.0,        # khoang cach toi thieu giua 2 su kien cung loai
    "save_annotated": True,           # luu them anh co khung danh dau
}


def load():
    cfg = json.loads(json.dumps(DEFAULTS))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user = json.load(f)
            for k, v in user.items():
                if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                    cfg[k].update(v)
                else:
                    cfg[k] = v
        except Exception as e:
            print("[cau hinh] Khong doc duoc config.json (%s), dung mac dinh." % e)
    return cfg


def save(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    return CONFIG_PATH
