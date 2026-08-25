# Hướng dẫn cài đặt trên máy mới

Tài liệu này dành cho người lần đầu đưa app sang một máy tính khác.
Nếu chỉ muốn biết app làm gì, xem [README.md](README.md).

---

## Tóm tắt: 4 bước

```
1. Cài Python  →  2. Cài & đăng nhập app Imou  →  3. Chạy CAI_DAT.cmd  →  4. Chọn vùng chụp
```

---

## Yêu cầu máy

| Hạng mục | Yêu cầu |
|---|---|
| Hệ điều hành | Windows 10 hoặc 11 (app dùng API riêng của Windows) |
| Python | 3.8 trở lên (đã kiểm thử trên **3.12**) |
| App Imou cho PC | Đã cài, **đã đăng nhập**, đã thấy camera trong danh sách |
| Kết nối mạng | Cần khi cài (tải thư viện + mô hình ~24 MB). Lúc chạy thì không cần mạng ngoài Imou |
| Card đồ hoạ | Không cần. Mô hình nhận dạng chạy bằng CPU |
| Ổ đĩa | ~200 MB cho app + khoảng **20 MB mỗi ngày** ảnh chụp |

App **không chạy được trên macOS/Linux** vì phụ thuộc `PrintWindow`, `pywin32` và
bộ OCR của Windows.

---

## Bước 1 — Cài Python

Tải tại <https://www.python.org/downloads/windows/>.

> ⚠️ Lúc cài **nhớ tích ô “Add python.exe to PATH”**, nếu không `CAI_DAT.cmd`
> sẽ báo không tìm thấy Python.

Kiểm tra: mở Command Prompt, gõ `python --version` — phải hiện số phiên bản.

---

## Bước 2 — Cài và đăng nhập app Imou

1. Cài **Imou cho PC** (bản Windows).
2. Đăng nhập tài khoản có camera cần theo dõi.
3. Mở camera xem thử một lần cho chắc là kết nối được.
4. Ghi lại **đúng tên camera** hiển thị trong app (ví dụ `AOV PT-BE57`).

App tìm cửa sổ Imou theo tiêu đề và điều khiển giao diện của nó, nên **app Imou
phải đang mở** lúc chạy (nếu bị tắt, app sẽ tự mở lại).

---

## Bước 3 — Chạy CAI_DAT.cmd

Chép cả thư mục dự án sang máy mới, rồi **bấm đúp `CAI_DAT.cmd`**. Nó sẽ:

1. Tìm Python trên máy;
2. Cài các thư viện: `opencv-python 4.10`, `numpy`, `mss`, `pywin32`, `pillow`, `winsdk`;
3. Đăng ký `pywin32` (một số máy cần bước này);
4. Tải mô hình nhận dạng **YOLOv4-tiny** vào thư mục `models/` nếu chưa có;
5. Kiểm tra bộ OCR của Windows và đường dẫn app Imou;
6. Hỏi có tạo **lịch tự động quét mỗi 3 tiếng** không.

Muốn kiểm tra lại bất cứ lúc nào mà không cài gì thêm:

```bat
python -m app.cai_dat --kiem-tra
```

### Nếu gặp lỗi

| Báo lỗi | Cách xử lý |
|---|---|
| `Chua cai Python` | Cài lại Python và **tích “Add python.exe to PATH”** |
| `OpenCV ... không nạp được mô hình Darknet` | Bản 5.x đã bỏ bộ nạp Darknet. Chạy `pip install "opencv-python==4.10.0.84"` |
| `Chưa dùng được OCR của Windows` | Settings → Time & language → Language & region → chọn ngôn ngữ → Language options → cài gói **OCR** |
| `Không thấy app Imou trên máy này` | Cài Imou cho PC, hoặc sửa `duong_dan_imou` trong `config.json` |
| Tải mô hình thất bại | Tải tay 3 file rồi bỏ vào `models/` (đường dẫn hiện trong thông báo lỗi) |

---

## Bước 4 — Chọn vùng chụp

Kích thước cửa sổ Imou mỗi máy một khác, nên phải chỉ cho app biết đâu là vùng
khung hình video.

1. Mở app Imou, xem camera;
2. Bấm đúp **`CHON_VUNG_CHUP.bat`**;
3. App tự dò vùng video và vẽ khung cam — bấm **Enter** nếu đúng, bấm **R** để tự kéo chuột chọn.

Vùng chụp được ghi vào `config.json`. **Nếu sau này bạn đổi kích thước cửa sổ
Imou thì chạy lại bước này.**

---

## Chỉnh cấu hình — `config.json`

Ba khoá cần để ý nhất khi sang máy mới:

```json
{
  "camera_name": "AOV PT-BE57",
  "duong_dan_imou": "C:\\Program Files\\Imou_en\\bin\\Imou_en.exe",
  "huong_xe": "ca_hai"
}
```

| Khoá | Ý nghĩa |
|---|---|
| `camera_name` | Phải **khớp tên hiển thị trong app Imou** — app dùng tên này để chọn đúng camera |
| `duong_dan_imou` | Đường dẫn file chạy của Imou (`CAI_DAT.cmd` tự điền nếu tìm thấy) |
| `huong_xe` | `ca_hai` = ghi nhận mọi lượt xe, không phân biệt hướng (mặc định). Đổi thành `trai_sang_phai` / `phai_sang_trai` nếu muốn chỉ đếm xe ra hoặc xe vào mỏ |

Toàn bộ các khoá còn lại xem bảng trong [README.md](README.md).

---

## Chạy thử

```bat
python -m app.main --su-kien --ngay hom-nay
```

Trong lúc chạy, **app tự điều khiển chuột** trên cửa sổ Imou (khoảng 10–30 phút
tuỳ số lượt xe trong ngày) — đừng dùng máy trong lúc đó.

Xong sẽ có:

- `index.html` — báo cáo gộp 3 ngày gần nhất
- `reports/BaoCao_toan_bo.html` — báo cáo đầy đủ mọi ngày
- `captures/SUKIEN-<ngày>/` — ảnh và dữ liệu thô

---

## Chạy tự động

`CAI_DAT.cmd` có hỏi tạo lịch. Tạo/sửa tay:

```bat
:: tao lich chay moi 3 tieng, bat dau 08:00
schtasks /Create /TN "HongHanh - Quet camera moi 3 gio" ^
   /TR "C:\duong\dan\den\TU_DONG_QUET.bat" /SC HOURLY /MO 3 /ST 08:00 /F

:: xem lich
schtasks /Query /TN "HongHanh - Quet camera moi 3 gio"

:: doi sang 6 tieng mot lan
schtasks /Change /TN "HongHanh - Quet camera moi 3 gio" /RI 360

:: tam tat
schtasks /Change /TN "HongHanh - Quet camera moi 3 gio" /DISABLE
```

Điều kiện để lịch chạy được: **máy bật, đã đăng nhập Windows**. Nhật ký mỗi lần
chạy nằm ở `nhatky_tudong.txt`.

---

## Đẩy báo cáo lên GitHub (không bắt buộc)

Chỉ cần nếu bạn muốn xem báo cáo qua đường link trên điện thoại.

```bat
:: 1. Cai Git for Windows: https://git-scm.com/download/win

:: 2. Trong thu muc du an
git init
git branch -M main
git add -A
git commit -m "Lan dau"

:: 3. Tao repo tren github.com roi noi vao
git remote add origin https://github.com/<tai-khoan>/<ten-repo>.git
git push -u origin main
```

Lần push đầu Git sẽ mở trình duyệt cho bạn đăng nhập; sau đó thông tin được lưu
trong Windows Credential Manager nên lịch tự động push được mà không hỏi lại.

Cuối cùng bật **GitHub Pages**: vào repo → Settings → Pages → Source chọn
`main` / `/ (root)`. Sau 1–2 phút truy cập được tại
`https://<tài-khoản>.github.io/<tên-repo>/`.

> Repo công khai thì ảnh công trường ai cũng xem được. Muốn kín thì để repo
> riêng tư — nhưng GitHub Pages trên repo riêng tư cần gói trả phí.

Để giữ dung lượng repo nhẹ, app chỉ đẩy **3 ngày gần nhất** (`app/git_sync.py`);
ảnh cũ vẫn còn đủ trong `captures/` ở máy.

---

## Gỡ cài đặt

```bat
schtasks /Delete /TN "HongHanh - Quet camera moi 3 gio" /F
```

Rồi xoá thư mục dự án. Các thư viện Python cài chung có thể gỡ bằng
`pip uninstall opencv-python mss pywin32 pillow winsdk`.
