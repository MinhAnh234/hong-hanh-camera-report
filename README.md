# App chụp ảnh xe & báo cáo HTML — Hong Hanh Company

📊 **Xem báo cáo trực tuyến: https://minhanh234.github.io/hong-hanh-camera-report/**
(mở được trên cả điện thoại)

Ứng dụng Python làm việc với camera **Imou AOV PT-BE57** qua app Imou trên máy tính,
xuất **báo cáo HTML** kèm ảnh và thống kê. App có **hai chế độ**:

| Chế độ | Nguồn phát hiện xe | Dùng khi nào |
|---|---|---|
| **A. Đọc sự kiện của camera** (khuyến nghị) | AI sẵn có trong camera – mục *Phát Hiện Phương Tiện* ở trung tâm tin nhắn Imou | Lấy lại lịch sử cả ngày, không cần mở máy suốt. Ảnh nét lấy từ clip ghi hình. |
| **B. Tự nhận dạng theo thời gian thực** | App tự chụp cửa sổ Imou + YOLOv4-tiny | Cần ảnh nét, khung hình đầy đủ, phân loại xe ben / xe ô tô / xe khách. Phải để máy chạy. |

Hai chế độ dùng chung định dạng dữ liệu và chung mẫu báo cáo, nên có thể dùng cả hai.

## Chạy app

| Việc cần làm | Cách chạy |
|---|---|
| Mở giao diện app | Bấm đúp **`CHAY_APP.bat`** |
| **Đọc sự kiện phương tiện của camera** (chế độ A) | Bấm đúp **`DOC_SU_KIEN_CAMERA.bat`** |
| Tự giám sát chạy nền (chế độ B) | Bấm đúp **`CHAY_NEN.bat`** (Ctrl+C để dừng) |
| Chọn lại vùng chụp | Bấm đúp **`CHON_VUNG_CHUP.bat`** |

Hoặc dùng dòng lệnh:

```bat
python -m app.main                      :: mở giao diện
python -m app.main --su-kien --ngay 23  :: chế độ A: đọc sự kiện + chụp ảnh nét
python -m app.main --su-kien --ngay hom-qua
python -m app.main --su-kien --khong-anh-net   :: nhanh, nhưng ảnh mờ
python -m app.main --nen --phut 60      :: chạy nền 60 phút rồi tự xuất báo cáo
python -m app.main --danh-sach          :: liệt kê các phiên đã ghi
python -m app.main --bao-cao <mã phiên> :: xuất lại báo cáo của một phiên
python -m app.select_roi                :: chọn lại vùng chụp (thêm --tay để kéo chuột)
```

**Yêu cầu:** mở sẵn app Imou và đang xem camera AOV PT-BE57. App **không cần** cửa sổ Imou
nằm trên cùng — nó dùng `PrintWindow` của Windows nên vẫn chụp được khi Imou bị che khuất.

## Chế độ A – đọc sự kiện phương tiện của camera

Camera AOV PT-BE57 tự phát hiện phương tiện và lưu sự kiện kèm ảnh. App điều khiển
giao diện Imou để lấy đúng dữ liệu đó:

```
Trung tâm tin nhắn ─► chọn camera ─► lọc "Phát Hiện Phương Tiện" ─► chọn ngày
        └─► quét từng thẻ sự kiện (tự cuộn) ─► ảnh + mốc thời gian ─► báo cáo HTML
```

Mốc thời gian được đọc bằng **OCR sẵn có của Windows** (bỏ phiếu qua nhiều lần đọc)
kết hợp **đối sánh mẫu chữ số**. Chữ trên thẻ chỉ cao ~9 điểm ảnh nên đôi khi vẫn đọc
lệch; những mốc chưa chắc chắn được đánh dấu **≈** ngay cạnh giờ trong báo cáo để đối
chiếu lại. Số lượt và ảnh thì luôn chính xác.

### Ảnh nét

Ảnh trong danh sách sự kiện của Imou chỉ là thumbnail **110×60** nên rất mờ. Vì vậy sau
khi lấy được các mốc giờ, app làm thêm một bước: mỗi sự kiện đều có một **clip ghi hình**
tương ứng trong *Xem Lại → Bản ghi nội bộ*, app tự mở đúng clip đó, phóng to cửa sổ phát,
chụp lại nhiều khung hình và **chọn khung có xe rõ nhất**:

```
sự kiện 15:43:16 ──khớp──► clip 15:43:15 ──phát──► chụp 10 khung hình
        └─► chọn khung YOLO thấy xe rõ nhất ─► ảnh 1545×848 + khoanh khung + nhãn xe
```

Nhờ vậy báo cáo còn biết luôn **loại xe** (xe ben / xe ô tô) chứ không chỉ "Phương tiện".
Muốn bỏ bước này cho nhanh thì thêm `--khong-anh-net` (ảnh sẽ mờ).

### Chỉ lấy xe ra khỏi mỏ (đi từ trái qua phải)

Trong lúc phát clip, app bám vết chiếc xe qua nhiều khung hình để biết nó đi
**trái → phải** (ra khỏi mỏ) hay **phải → trái** (vào mỏ). Chỉ lượt ra khỏi mỏ
mới được đưa vào báo cáo:

```
15:17:07  ← clip 15:17:07   ✔ xe ben 86% – hướng trái → phải (ra khỏi mỏ)
14:57:00  ← clip 14:56:58   ⏭ bỏ qua: xe đi phải → trái (lệch ngang -164 px)
```

Chỉnh trong `config.json`:

| Khoá | Ý nghĩa | Mặc định |
|---|---|---|
| `huong_xe` | `trai_sang_phai` / `phai_sang_trai` / `ca_hai` | `trai_sang_phai` |
| `huong_min_dx` | Xe phải dịch ngang ít nhất bao nhiêu điểm ảnh mới kết luận hướng | `25` |
| `giu_khi_khong_ro_huong` | Vẫn giữ lượt không đoán được hướng (xe đứng yên, chỉ thấy 1 khung hình) | `true` |

Lọc hướng **chỉ hoạt động khi có bước chụp ảnh nét** — chạy với `--khong-anh-net`
thì không biết hướng nên giữ tất cả.

Lưu ý khi chạy chế độ A:
- App **tự điều khiển chuột** và đưa cửa sổ Imou lên trên → đừng dùng chuột trong lúc
  chạy (khoảng 4–6 phút cho một ngày ~10 sự kiện).
- Nếu app Imou đang thu nhỏ, app sẽ tự khôi phục cửa sổ.

## Chế độ B – tự nhận dạng theo thời gian thực

```
Cửa sổ Imou ──PrintWindow──► cắt vùng video (ROI)
      │
      ├─ tách nền MOG2  → tìm vùng đang chuyển động
      ├─ chỉ quét YOLO ở những ô lưới có chuyển động  (xe ở xa nên phải quét theo ô)
      ├─ cắt sát khung xe, quét lại ở 608px để phân loại đúng xe ben / xe con
      ├─ bám vết giữa các khung hình → mỗi lượt xe chỉ sinh 1 sự kiện
      └─ lưu ảnh gốc + ảnh đánh dấu + events.json  →  báo cáo HTML
```

Vì camera đặt xa, xe chỉ chiếm khoảng 40–70 điểm ảnh. Nếu đưa cả khung hình vào mạng
nhận dạng thì xe bị thu nhỏ và không nhận ra được — nên app **quét theo ô** rồi **phóng to
để phân loại lại**. Nhãn cuối cùng của một lượt xe do các khung hình **bỏ phiếu** (trọng số
là độ tin cậy), tránh việc mô hình lúc đọc "car" lúc đọc "truck".

## Kết quả sinh ra

```
captures/SUKIEN-<ngày>/
    001_truck_20260823-163711.jpg           ← ảnh gốc toàn khung hình
    001_truck_20260823-163711_danhdau.jpg   ← ảnh có khung + nhãn + mã lượt
    events.json                             ← dữ liệu thô của ngày đó
index.html                                  ← BÁO CÁO GỘP (3 ngày gần nhất) – đẩy lên web
reports/BaoCao_toan_bo.html                 ← báo cáo gộp ĐẦY ĐỦ mọi ngày (chỉ ở máy)
```

**Tất cả các ngày nằm chung MỘT báo cáo**, không tách file theo ngày. Trong bảng có
thêm ô lọc **Ngày** bên cạnh ô lọc giờ và loại xe.

### Dung lượng GitHub

Chỉ **3 ngày gần nhất** được đẩy lên GitHub; các ngày cũ hơn được gỡ khỏi repo nhưng
**vẫn còn nguyên trong thư mục `captures/` ở máy**. Việc này do `app/git_sync.py` lo:
nó chạy `git rm --cached` (không xoá file) và ghi vào `.git/info/exclude` để lần sau
không thêm lại.

```bat
python -m app.git_sync          :: dọn thủ công
```

Đổi số ngày giữ lại: sửa `NGAY_TREN_WEB` trong `app/report.py` và `NGAY_MAC_DINH`
trong `app/git_sync.py`.

Báo cáo HTML là **một bảng danh sách gọn, 4 cột**:

| STT | Thời gian | Loại xe | Hình ảnh |
|---|---|---|---|

- **Phóng to ảnh tuỳ ý**: bấm vào ảnh → lăn chuột để zoom (tới ~1200%), kéo để di chuyển,
  nháy đúp để phóng nhanh, nút −/+/⤢ hoặc phím `+` `-` `0`, `Esc` để đóng.
- **Lọc danh sách**: chọn khoảng giờ (*Từ … đến …*) và/hoặc *Loại xe*; góc phải hiện
  `n/N lượt`. Bấm **Xoá lọc** để bỏ lọc. STT giữ nguyên theo thứ tự gốc.
- **Nút 📱 Xem trên điện thoại**: chuyển sang bố cục thẻ dọc (ảnh to hết bề ngang),
  bấm lại để về bố cục bảng. Mở bằng điện thoại thì tự vào bố cục này.
- Mốc giờ nào đọc chưa chắc chắn sẽ có dấu **≈** ngay cạnh (rê chuột để xem chú thích).

## Chỉnh cấu hình — `config.json`

| Khoá | Ý nghĩa | Mặc định |
|---|---|---|
| `camera_name` | Tên camera – cũng dùng để tìm đúng camera trong danh sách Imou | `AOV PT-BE57` |
| `window_title` | Tìm cửa sổ theo tiêu đề | `Imou` |
| `capture_mode` | `auto` (ưu tiên PrintWindow) hoặc `manhinh` | `auto` |
| `roi` | Vùng video, theo tỉ lệ 0–1 của cửa sổ | tự dò |
| `fps` | Số khung hình xử lý mỗi giây | `3.0` |
| `watch_classes` | Loại xe cần bắt (`car`, `truck`, `bus`, thêm `motorbike` nếu muốn bắt xe máy) | `car, truck, bus` |
| `conf_threshold` | Ngưỡng tin cậy nhận dạng | `0.30` |
| `input_size` | Độ phân giải mỗi ô quét (nhỏ = nhanh) | `320` |
| `scan_max_regions` | Số ô quét tối đa mỗi khung hình | `8` |
| `refine_labels` | Quét lại ở độ phân giải cao để phân loại | `true` |
| `track_min_hits` | Số lần thấy tối thiểu để tính là một lượt | `2` |
| `track_min_move_px` | Quãng đường tối thiểu để coi là "đang chuyển động" | `5` |
| `event_cooldown_sec` | Khoảng cách tối thiểu giữa 2 lượt cùng loại | `3.0` |
| `min_motion_in_box` | Lọc theo tỉ lệ chuyển động trong khung xe (0 = tắt) | `0.0` |

**Bắt hụt xe?** Giảm `conf_threshold` (0.20), giảm `track_min_hits` xuống 1,
hoặc tăng `input_size` lên 416.
**Báo nhầm quá nhiều?** Tăng `conf_threshold` (0.45), tăng `track_min_move_px` (10–20).

## Thư viện

`opencv-python 4.10` (bản 5.x đã bỏ bộ nạp Darknet nên **không dùng được**),
`numpy`, `mss`, `pywin32`, `pillow`, `winsdk` (dùng OCR sẵn có của Windows).

```bat
python -m pip install "opencv-python==4.10.0.84" numpy mss pywin32 pillow winsdk
```

Mô hình nhận dạng: **YOLOv4-tiny** (COCO) trong thư mục `models/` — chạy trên CPU,
không cần GPU, không cần kết nối mạng khi chạy.

## Chạy tự động & đồng bộ lên GitHub

`TU_DONG_QUET.bat` làm 3 việc: quét sự kiện của hôm nay → sinh lại `index.html`
→ `git push` lên GitHub. GitHub Pages tự cập nhật sau 1–2 phút.

Đã tạo sẵn lịch trong Windows Task Scheduler, **chạy mỗi 3 tiếng**:

```bat
:: xem lịch
schtasks /Query /TN "HongHanh - Quet camera moi 3 gio"

:: đổi sang 6 tiếng/lần
schtasks /Change /TN "HongHanh - Quet camera moi 3 gio" /RI 360

:: tạm tắt / bật lại
schtasks /Change /TN "HongHanh - Quet camera moi 3 gio" /DISABLE
schtasks /Change /TN "HongHanh - Quet camera moi 3 gio" /ENABLE
```

Nhật ký mỗi lần chạy nằm trong `nhatky_tudong.txt` (không đẩy lên GitHub).

**Điều kiện để lịch chạy được:** máy đang bật, đã đăng nhập Windows, app Imou đang mở.
Trong lúc quét (~4–6 phút) app chiếm chuột và đưa cửa sổ Imou lên trên cùng.
