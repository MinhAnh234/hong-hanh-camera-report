# -*- coding: utf-8 -*-
"""Giao dien app: chon viec, bam CHAY, xem tien do, bam DUNG bat cu luc nao."""
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

from . import chay, config, huy, storage

VIEC = [
    ("su_kien", u"Đọc sự kiện camera + chụp ảnh nét",
     u"Lấy các lượt camera đã phát hiện phương tiện, rồi mở clip tương ứng\n"
     u"để chụp lại ảnh nét và xác định hướng xe. (khoảng 10–30 phút)"),
    ("su_kien_nhanh", u"Đọc sự kiện camera (nhanh, ảnh mờ)",
     u"Chỉ lấy danh sách lượt và ảnh thu nhỏ của Imou. Nhanh (1–2 phút)\n"
     u"nhưng ảnh mờ và không lọc được hướng xe."),
    ("duyet_clip", u"Duyệt lần lượt từng clip ghi hình",
     u"Mở clip đầu rồi dùng nút › đi hết các clip trong ngày, tự tìm xe\n"
     u"và hướng di chuyển. Chậm nhưng ít phụ thuộc giao diện nhất."),
]


class App(object):
    def __init__(self, root):
        self.root = root
        self.cfg = config.load()
        self.q = queue.Queue()
        self.luong = None

        root.title(u"App chụp ảnh xe – Hong Hanh Company")
        root.geometry("980x680")
        root.minsize(860, 600)
        self._dung_giao_dien()
        self._doi_trang_thai(False)
        self.root.after(120, self._bom)
        self.root.protocol("WM_DELETE_WINDOW", self._dong)

    # ------------------------------------------------------------ giao dien
    def _dung_giao_dien(self):
        dau = ttk.Frame(self.root, padding=(14, 12, 14, 6))
        dau.pack(fill="x")
        ttk.Label(dau, text=u"Giám sát xe ra khỏi mỏ",
                  font=("Segoe UI", 15, "bold")).pack(side="left")
        self.lbl_cam = ttk.Label(dau, foreground="#5b6577",
                                 text=u"Camera: %s" % self.cfg.get("camera_name", ""))
        self.lbl_cam.pack(side="right")

        # --- chon viec ---
        khung = ttk.LabelFrame(self.root, text=u" Chọn việc cần chạy ", padding=12)
        khung.pack(fill="x", padx=14, pady=(4, 8))
        self.viec = tk.StringVar(value=VIEC[0][0])
        for ma, ten, mo_ta in VIEC:
            o = ttk.Frame(khung)
            o.pack(fill="x", pady=3)
            ttk.Radiobutton(o, text=ten, value=ma, variable=self.viec).pack(anchor="w")
            ttk.Label(o, text=mo_ta, foreground="#6b7480",
                      font=("Segoe UI", 8)).pack(anchor="w", padx=24)

        # --- ngay + nut ---
        hang = ttk.Frame(self.root, padding=(14, 0))
        hang.pack(fill="x")
        ttk.Label(hang, text=u"Ngày:").pack(side="left")
        self.ngay = tk.StringVar(value=u"hom-nay")
        ttk.Entry(hang, textvariable=self.ngay, width=14).pack(side="left", padx=(6, 4))
        ttk.Label(hang, text=u"(hom-nay | hom-qua | 24 | 2026-08-24)",
                  foreground="#6b7480", font=("Segoe UI", 8)).pack(side="left")

        self.nut_chay = ttk.Button(hang, text=u"▶  CHẠY", command=self.chay)
        self.nut_chay.pack(side="right")
        self.nut_dung = ttk.Button(hang, text=u"■  DỪNG", command=self.dung)
        self.nut_dung.pack(side="right", padx=(0, 8))

        # --- trang thai ---
        tt = ttk.Frame(self.root, padding=(14, 10))
        tt.pack(fill="x")
        self.thanh = ttk.Progressbar(tt, mode="indeterminate")
        self.thanh.pack(fill="x")

        # --- nhat ky ---
        nk = ttk.LabelFrame(self.root, text=u" Tiến độ ", padding=8)
        nk.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        self.log = scrolledtext.ScrolledText(nk, height=14, wrap="word",
                                             font=("Consolas", 9))
        self.log.pack(fill="both", expand=True)
        self.log.configure(state="disabled")

        # --- nut phu ---
        phu = ttk.Frame(self.root, padding=(14, 0, 14, 10))
        phu.pack(fill="x")
        ttk.Button(phu, text=u"Mở báo cáo", command=self.mo_bao_cao).pack(side="left")
        ttk.Button(phu, text=u"Mở thư mục ảnh",
                   command=self.mo_thu_muc).pack(side="left", padx=(8, 0))
        ttk.Button(phu, text=u"Chọn vùng chụp",
                   command=self.chon_vung).pack(side="left", padx=(8, 0))
        ttk.Button(phu, text=u"Đẩy lên GitHub",
                   command=self.day_github).pack(side="left", padx=(8, 0))
        self.lbl_tt = ttk.Label(phu, text=u"Sẵn sàng", foreground="#5b6577")
        self.lbl_tt.pack(side="right")

    def _doi_trang_thai(self, dang_chay):
        self.nut_chay.state(["disabled"] if dang_chay else ["!disabled"])
        self.nut_dung.state(["!disabled"] if dang_chay else ["disabled"])
        if dang_chay:
            self.thanh.start(12)
        else:
            self.thanh.stop()

    # ------------------------------------------------------------ chay viec
    def chay(self):
        if self.luong and self.luong.is_alive():
            return
        self.cfg = config.load()
        self.lbl_cam.config(text=u"Camera: %s" % self.cfg.get("camera_name", ""))
        ma = self.viec.get()
        ngay = self.ngay.get().strip() or "hom-nay"

        if not messagebox.askokcancel(
                u"Bắt đầu",
                u"App sẽ tự điều khiển chuột trên cửa sổ Imou.\n"
                u"Đừng dùng chuột trong lúc chạy.\n\n"
                u"Bấm DỪNG bất cứ lúc nào để ngắt."):
            return

        self._xoa_log()
        self._ghi(u"=== %s | %s ===" % (dict((m, t) for m, t, _d in VIEC)[ma], ngay))
        self._doi_trang_thai(True)
        self.lbl_tt.config(text=u"Đang chạy…")
        self.luong = threading.Thread(target=self._chay_nen, args=(ma, ngay),
                                      daemon=True)
        self.luong.start()

    def _chay_nen(self, ma, ngay):
        def log(*p):
            self.q.put(("log", u" ".join(str(x) for x in p)))
        try:
            if ma == "su_kien":
                kq = chay.quet_su_kien(ngay, anh_net=True, log=log)
            elif ma == "su_kien_nhanh":
                kq = chay.quet_su_kien(ngay, anh_net=False, log=log)
            else:
                kq = chay.duyet_clip(ngay, log=log)
            self.q.put(("xong", kq))
        except huy.DaDung:
            self.q.put(("dung", None))
        except Exception as e:
            self.q.put(("loi", u"%s" % e))

    def dung(self):
        huy.yeu_cau_dung()
        self.lbl_tt.config(text=u"Đang dừng…")
        self._ghi(u"⏹ Đã yêu cầu dừng, chờ kết thúc việc đang làm dở…")

    # ------------------------------------------------------------ nut phu
    def mo_bao_cao(self):
        for p in (os.path.join(storage.ROOT, "index.html"),
                  os.path.join(storage.REPORT_DIR, "BaoCao_toan_bo.html")):
            if os.path.exists(p):
                os.startfile(p)
                return
        messagebox.showinfo(u"Chưa có", u"Chưa có báo cáo nào. Hãy chạy một lượt trước.")

    def mo_thu_muc(self):
        os.makedirs(storage.CAPTURE_DIR, exist_ok=True)
        os.startfile(storage.CAPTURE_DIR)

    def chon_vung(self):
        if self.luong and self.luong.is_alive():
            messagebox.showinfo(u"Đang chạy", u"Hãy dừng việc đang chạy trước.")
            return
        subprocess.call([sys.executable, "-m", "app.select_roi"], cwd=storage.ROOT)
        self.cfg = config.load()
        messagebox.showinfo(u"Vùng chụp", u"Vùng chụp hiện tại:\n%s" % self.cfg["roi"])

    def day_github(self):
        if self.luong and self.luong.is_alive():
            messagebox.showinfo(u"Đang chạy", u"Hãy dừng việc đang chạy trước.")
            return
        self._doi_trang_thai(True)
        self.lbl_tt.config(text=u"Đang đẩy lên GitHub…")

        def viec():
            try:
                chay.day_len_github(log=lambda *p: self.q.put(
                    ("log", u" ".join(str(x) for x in p))))
                self.q.put(("xong", None))
            except Exception as e:
                self.q.put(("loi", u"%s" % e))

        self.luong = threading.Thread(target=viec, daemon=True)
        self.luong.start()

    # ------------------------------------------------------------ nhat ky
    def _xoa_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _ghi(self, dong):
        self.log.configure(state="normal")
        self.log.insert("end", u"%s  %s\n" % (datetime.now().strftime("%H:%M:%S"), dong))
        self.log.see("end")
        self.log.configure(state="disabled")

    def _bom(self):
        try:
            while True:
                loai, du_lieu = self.q.get_nowait()
                if loai == "log":
                    self._ghi(du_lieu)
                elif loai == "xong":
                    self._doi_trang_thai(False)
                    if isinstance(du_lieu, dict):
                        self._ghi(u"✔ Xong: %d lượt%s"
                                  % (du_lieu["so_luot"],
                                     u" (bỏ %d lượt sai hướng)" % du_lieu["so_bo"]
                                     if du_lieu["so_bo"] else u""))
                        self.lbl_tt.config(text=u"Xong – %d lượt" % du_lieu["so_luot"])
                        if du_lieu.get("bao_cao") and messagebox.askyesno(
                                u"Xong", u"Ghi nhận %d lượt.\nMở báo cáo ngay?"
                                         % du_lieu["so_luot"]):
                            os.startfile(du_lieu["bao_cao"])
                    else:
                        self.lbl_tt.config(text=u"Xong")
                elif loai == "dung":
                    self._doi_trang_thai(False)
                    self._ghi(u"⏹ Đã dừng theo yêu cầu.")
                    self.lbl_tt.config(text=u"Đã dừng")
                elif loai == "loi":
                    self._doi_trang_thai(False)
                    self._ghi(u"✖ Lỗi: %s" % du_lieu)
                    self.lbl_tt.config(text=u"Có lỗi")
                    messagebox.showerror(u"Lỗi", du_lieu)
        except queue.Empty:
            pass
        self.root.after(120, self._bom)

    def _dong(self):
        if self.luong and self.luong.is_alive():
            if not messagebox.askokcancel(u"Đang chạy",
                                          u"Việc đang chạy sẽ bị dừng. Thoát?"):
                return
            huy.yeu_cau_dung()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("vista")
    except Exception:
        pass
    App(root)
    root.mainloop()
    return 0
