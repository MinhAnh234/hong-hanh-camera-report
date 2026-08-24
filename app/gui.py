# -*- coding: utf-8 -*-
"""Giao dien dieu khien app: xem truc tiep, dem luot xe, xuat bao cao HTML."""
import os
import queue
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

import cv2
from PIL import Image, ImageTk

from . import config, report, storage
from .engine import MonitorEngine

BOX_COLOR = {"truck": (0, 165, 255), "bus": (0, 200, 255), "car": (60, 220, 60)}
PREVIEW_W, PREVIEW_H = 640, 360


class App(object):
    def __init__(self, root):
        self.root = root
        self.cfg = config.load()
        self.q = queue.Queue(maxsize=200)
        self.engine = None
        self.last_photo = None
        self.count = {"truck": 0, "car": 0, "bus": 0}

        root.title(u"App chụp ảnh xe – Hong Hanh Company")
        root.geometry("1080x720")
        root.minsize(940, 640)

        self._build()
        self._set_state(False)
        self.root.after(120, self._pump)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- giao dien ----------
    def _build(self):
        top = ttk.Frame(self.root, padding=(12, 10))
        top.pack(fill="x")
        ttk.Label(top, text=u"Giám sát xe qua camera", font=("Segoe UI", 14, "bold")).pack(side="left")
        self.lbl_cam = ttk.Label(top, text=u"Camera: %s" % self.cfg.get("camera_name", ""),
                                 foreground="#5b6577")
        self.lbl_cam.pack(side="right")

        bar = ttk.Frame(self.root, padding=(12, 0))
        bar.pack(fill="x")
        self.btn_start = ttk.Button(bar, text=u"▶  Bắt đầu giám sát", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(bar, text=u"■  Dừng", command=self.stop)
        self.btn_stop.pack(side="left", padx=(8, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Button(bar, text=u"Chọn vùng chụp", command=self.select_roi).pack(side="left")
        ttk.Button(bar, text=u"Xuất báo cáo HTML", command=self.export).pack(side="left", padx=(8, 0))
        ttk.Button(bar, text=u"Mở thư mục ảnh", command=self.open_folder).pack(side="left", padx=(8, 0))
        ttk.Separator(bar, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Button(bar, text=u"Đọc sự kiện từ camera",
                   command=self.doc_su_kien).pack(side="left")

        body = ttk.Frame(self.root, padding=12)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(1, weight=1)

        # --- the thong ke ---
        cards = ttk.Frame(body)
        cards.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.card_vals = {}
        for i, (key, text) in enumerate(
            [("tong", u"Tổng lượt"), ("truck", u"Xe ben / tải"), ("car", u"Xe ô tô"),
             ("bus", u"Xe khách"), ("frames", u"Khung hình"), ("motion", u"Lần c.động")]
        ):
            f = ttk.Frame(cards, relief="solid", borderwidth=1, padding=(12, 8))
            f.grid(row=0, column=i, sticky="ew", padx=(0 if i == 0 else 8, 0))
            cards.columnconfigure(i, weight=1)
            ttk.Label(f, text=text, foreground="#5b6577", font=("Segoe UI", 8)).pack(anchor="w")
            v = ttk.Label(f, text="0", font=("Segoe UI", 17, "bold"))
            v.pack(anchor="w")
            self.card_vals[key] = v

        # --- xem truc tiep ---
        left = ttk.LabelFrame(body, text=u" Vùng chụp (xem trực tiếp) ", padding=8)
        left.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        self.canvas = tk.Canvas(left, width=PREVIEW_W, height=PREVIEW_H, bg="#101418",
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_text(PREVIEW_W // 2, PREVIEW_H // 2, text=u"Chưa bắt đầu",
                                fill="#6b7480", font=("Segoe UI", 11), tags="hint")

        # --- nhat ky ---
        right = ttk.LabelFrame(body, text=u" Nhật ký lượt xe ", padding=8)
        right.grid(row=1, column=1, sticky="nsew")
        cols = ("ma", "gio", "loai", "tincay")
        self.tree = ttk.Treeview(right, columns=cols, show="headings", height=14)
        for c, t, w in (("ma", u"Mã lượt", 150), ("gio", u"Thời gian", 78),
                        ("loai", u"Loại xe", 110), ("tincay", u"Tin cậy", 60)):
            self.tree.heading(c, text=t)
            self.tree.column(c, width=w, anchor="w")
        sb = ttk.Scrollbar(right, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        # --- thanh trang thai ---
        status = ttk.Frame(self.root, relief="groove", padding=(12, 6))
        status.pack(fill="x", side="bottom")
        self.lbl_status = ttk.Label(status, text=u"Sẵn sàng")
        self.lbl_status.pack(side="left")
        self.lbl_session = ttk.Label(status, text=u"", foreground="#5b6577")
        self.lbl_session.pack(side="right")

    def _set_state(self, running):
        self.btn_start.state(["disabled"] if running else ["!disabled"])
        self.btn_stop.state(["!disabled"] if running else ["disabled"])

    # ---------- dieu khien ----------
    def start(self):
        self.cfg = config.load()
        self.lbl_cam.config(text=u"Camera: %s" % self.cfg.get("camera_name", ""))
        self.engine = MonitorEngine(
            self.cfg,
            on_event=lambda ev, tr: self._put(("event", ev)),
            on_status=lambda st: self._put(("status", st)),
            on_frame=lambda f, d: self._put(("frame", (f, d))),
        )
        try:
            session = self.engine.start()
        except Exception as e:
            messagebox.showerror(u"Lỗi", u"Không khởi động được: %s" % e)
            return
        self.count = {"truck": 0, "car": 0, "bus": 0}
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.lbl_session.config(text=u"Phiên: %s" % session.session_id)
        self.canvas.delete("hint")
        self._set_state(True)

    def stop(self):
        if not self.engine:
            return
        sid = self.engine.session.session_id if self.engine.session else None
        self.engine.stop()
        self._set_state(False)
        self.lbl_status.config(text=u"Đã dừng")
        if sid and self.engine.stats["su_kien"] > 0:
            if messagebox.askyesno(u"Xuất báo cáo",
                                   u"Phiên đã dừng với %d lượt xe.\nXuất báo cáo HTML ngay?"
                                   % self.engine.stats["su_kien"]):
                self._export_session(sid)

    def select_roi(self):
        if self.engine and self.engine.running:
            messagebox.showinfo(u"Đang chạy", u"Hãy dừng giám sát trước khi chọn lại vùng chụp.")
            return
        subprocess.call([sys.executable, "-m", "app.select_roi"], cwd=storage.ROOT)
        self.cfg = config.load()
        messagebox.showinfo(u"Vùng chụp", u"Vùng chụp hiện tại:\n%s" % self.cfg["roi"])

    def export(self):
        sid = None
        if self.engine and self.engine.session:
            sid = self.engine.session.session_id
        else:
            sessions = storage.list_sessions()
            sid = sessions[0] if sessions else None
        if not sid:
            messagebox.showinfo(u"Chưa có dữ liệu", u"Chưa có phiên nào để xuất báo cáo.")
            return
        self._export_session(sid)

    def _export_session(self, sid):
        try:
            path = report.build(sid)
        except Exception as e:
            messagebox.showerror(u"Lỗi", u"Không xuất được báo cáo: %s" % e)
            return
        self.lbl_status.config(text=u"Đã xuất: %s" % os.path.basename(path))
        try:
            os.startfile(path)
        except Exception:
            messagebox.showinfo(u"Đã xuất báo cáo", path)

    def doc_su_kien(self):
        """Lay danh sach su kien 'phat hien phuong tien' ma camera da tu ghi."""
        if self.engine and self.engine.running:
            messagebox.showinfo(u"Đang chạy",
                                u"Hãy dừng giám sát trước khi đọc sự kiện từ camera.")
            return
        ngay = simpledialog.askstring(
            u"Đọc sự kiện từ camera",
            u"Lấy sự kiện phát hiện phương tiện của ngày nào? "
            u"(để trống = hôm nay; hoặc 23 | 23-08 | 2026-08-23 | hom-qua)",
            parent=self.root)
        if ngay is None:
            return
        if not messagebox.askokcancel(
                u"Lưu ý",
                u"App sẽ tự điều khiển chuột trên cửa sổ Imou để mở trung tâm tin nhắn "
                u"và quét danh sách sự kiện. "
                u"Đừng dùng chuột trong lúc chạy (khoảng 1–2 phút)."):
            return
        self.lbl_status.config(text=u"Đang đọc sự kiện từ camera…")
        self.root.update_idletasks()
        cmd = 'start "Doc su kien camera" cmd /k ""%s" -m app.main --su-kien --ngay %s"' % (
            sys.executable, (ngay or "").strip() or "hom-nay")
        subprocess.Popen(cmd, cwd=storage.ROOT, shell=True)

    def open_folder(self):
        target = storage.CAPTURE_DIR
        if self.engine and self.engine.session:
            target = self.engine.session.dir
        os.makedirs(target, exist_ok=True)
        os.startfile(target)

    # ---------- cau noi luong ----------
    def _put(self, item):
        try:
            self.q.put_nowait(item)
        except queue.Full:
            pass

    def _pump(self):
        frame_item = None
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "frame":
                    frame_item = payload          # chi ve khung hinh moi nhat
                elif kind == "event":
                    self._on_event(payload)
                elif kind == "status":
                    self._on_status(payload)
        except queue.Empty:
            pass
        if frame_item is not None:
            self._draw(*frame_item)
        self.root.after(120, self._pump)

    def _on_event(self, ev):
        self.count[ev["loai_xe"]] = self.count.get(ev["loai_xe"], 0) + 1
        self.tree.insert("", 0, values=(
            ev["ma_luot"], ev["thoi_gian"][11:], ev["loai_xe_vi"],
            u"%.0f%%" % (ev["do_tin_cay"] * 100)))
        for k in ("truck", "car", "bus"):
            self.card_vals[k].config(text=str(self.count.get(k, 0)))
        self.card_vals["tong"].config(text=str(sum(self.count.values())))

    def _on_status(self, st):
        self.card_vals["frames"].config(text=str(st.get("khung_hinh", 0)))
        self.card_vals["motion"].config(text=str(st.get("lan_chuyen_dong", 0)))
        msg = st.get("trang_thai", "")
        if st.get("loi"):
            msg = u"%s – %s" % (msg, st["loi"])
        self.lbl_status.config(text=msg)

    def _draw(self, frame, dets):
        img = frame.copy()
        for d in dets:
            x, y, w, h = d.box
            color = BOX_COLOR.get(d.label, (0, 200, 255))
            cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
            cv2.putText(img, "%s %.0f%%" % (d.label, d.conf * 100), (x, max(16, y - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2, cv2.LINE_AA)

        cw = max(self.canvas.winfo_width(), 100)
        ch = max(self.canvas.winfo_height(), 100)
        fh, fw = img.shape[:2]
        scale = min(cw / float(fw), ch / float(fh))
        img = cv2.resize(img, (max(1, int(fw * scale)), max(1, int(fh * scale))))
        pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        self.last_photo = ImageTk.PhotoImage(pil)
        self.canvas.delete("all")
        self.canvas.create_image(cw // 2, ch // 2, image=self.last_photo)

    def _on_close(self):
        try:
            if self.engine and self.engine.running:
                self.engine.stop()
        finally:
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
