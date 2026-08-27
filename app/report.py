# -*- coding: utf-8 -*-
"""Sinh file bao cao HTML: mot bang danh sach gon, anh bam vao phong to duoc."""
import html
import os
from collections import Counter
from datetime import datetime

from . import storage

ROOT = storage.ROOT
REPORT_DIR = storage.REPORT_DIR
_NL = chr(10)

VI = {u"truck": u"Xe ben / xe tải", u"car": u"Xe ô tô", u"bus": u"Xe khách",
      u"vehicle": u"Phương tiện", u"motorbike": u"Xe máy", u"motorcycle": u"Xe máy"}

TEMPLATE = u"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TIEUDE__</title>
<style>
:root{
  --bg:#f4f6fa; --card:#ffffff; --ink:#131722; --muted:#5b6577; --line:#e2e7f0;
  --accent:#1f6feb; --ben:#f59e0b; --oto:#22a06b; --khach:#0ea5e9; --khac:#8b93a1;
  --shadow:0 1px 3px rgba(16,24,40,.08),0 8px 24px rgba(16,24,40,.06);
}
@media (prefers-color-scheme: dark){
  :root{ --bg:#0e1116; --card:#161b22; --ink:#e6edf3; --muted:#9aa4b2; --line:#252c37;
         --accent:#4b93ff; --shadow:0 1px 3px rgba(0,0,0,.5); }
}
*{box-sizing:border-box}
html,body{max-width:100%;overflow-x:hidden}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:"Segoe UI",system-ui,-apple-system,Roboto,Arial,sans-serif;line-height:1.5}
.wrap{max-width:1000px;margin:0 auto;padding:26px 18px 56px}
h1{margin:0 0 4px;font-size:27px;letter-spacing:-.01em}
.sub{color:var(--muted);font-size:15px;margin:0;flex:1 1 260px;min-width:0}
.sub b{color:var(--ink);font-weight:600}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);
  border-radius:12px;box-shadow:var(--shadow)}
table{width:100%;border-collapse:collapse;font-size:17px}
th,td{padding:14px 16px;text-align:left;border-bottom:1px solid var(--line);vertical-align:middle}
th{background:rgba(127,127,127,.07);font-size:13px;text-transform:uppercase;
  letter-spacing:.05em;color:var(--muted);font-weight:600;white-space:nowrap}
tr:last-child td{border-bottom:none}
td.stt{width:64px;text-align:center;color:var(--muted);font-size:18px;
  font-weight:600;font-variant-numeric:tabular-nums}
td.gio{width:215px;font-family:Consolas,"Courier New",monospace;font-size:16px;white-space:nowrap}
td.loai{width:180px}
td.anh{width:auto}
.uoc{color:var(--muted);cursor:help}
.pill{display:inline-block;padding:5px 14px;border-radius:20px;font-size:15px;
  font-weight:700;color:#1b1b1b;background:var(--khac)}
.pill.truck{background:var(--ben)} .pill.car{background:var(--oto);color:#fff}
.pill.bus{background:var(--khach);color:#fff} .pill.vehicle{background:var(--accent);color:#fff}
td.anh img{width:300px;height:169px;object-fit:cover;display:block;border-radius:8px;
  background:#000;cursor:zoom-in;border:1px solid var(--line)}
td.anh img:hover{outline:2px solid var(--accent);outline-offset:1px}
.empty{padding:36px;text-align:center;color:var(--muted)}
.thanh{display:flex;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:14px}
.loc{display:flex;align-items:center;gap:12px;flex-wrap:wrap;background:var(--card);
  border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-bottom:16px;
  box-shadow:var(--shadow);font-size:15px}
.loc label{display:flex;align-items:center;gap:7px;color:var(--muted);font-weight:600}
.loc input,.loc select{font:inherit;color:var(--ink);background:var(--bg);
  border:1px solid var(--line);border-radius:8px;padding:7px 10px}
.loc input:focus,.loc select:focus{outline:2px solid var(--accent);outline-offset:-1px}
.loc .xoa{background:none;border:1px solid var(--line);border-radius:8px;padding:7px 14px;
  font:inherit;font-weight:600;color:var(--muted);cursor:pointer}
.loc .xoa:hover{border-color:var(--accent);color:var(--accent)}
.loc .dem{margin-left:auto;color:var(--muted);font-weight:600;white-space:nowrap}
tr.an{display:none!important}
#khongco{display:none;padding:36px;text-align:center;color:var(--muted)}
#khongco.hien{display:block}
.nut{margin-left:auto;flex:0 0 auto;background:var(--card);color:var(--ink);border:1px solid var(--line);
  border-radius:999px;padding:9px 18px;font:600 15px/1 inherit;font-family:inherit;
  cursor:pointer;box-shadow:var(--shadow);white-space:nowrap}
.nut:hover{border-color:var(--accent);color:var(--accent)}

/* --- che do dien thoai: moi luot xe la mot the doc --- */
body.dt .wrap{max-width:min(520px,100%)}
body.dt .tablewrap{width:100%;max-width:min(430px,100%);margin:0 auto;border-radius:30px;
  border:11px solid #262b35;padding:8px 0;overflow:visible}
body.dt thead{display:none}
body.dt table,body.dt tbody,body.dt tr{display:block;width:100%}
body.dt tr{padding:14px 0;border-bottom:1px solid var(--line)}
body.dt tr:last-child{border-bottom:none}
body.dt td{display:inline-block;width:auto;max-width:100%;border:none;
  padding:2px 8px 2px 0;vertical-align:middle}
body.dt td.stt{padding-left:16px}
body.dt td.stt{text-align:left;font-size:17px}
body.dt td.gio{font-size:15px}
body.dt td.anh{display:block;width:100%;padding:10px 0 0}
body.dt td.anh img{display:block;width:100%;max-width:100%;height:auto;
  aspect-ratio:16/9;border-radius:0;border-left:none;border-right:none}
@media (max-width:760px){
  .wrap{padding:18px 12px 40px}
  td.anh img{width:100%;height:auto;aspect-ratio:16/9}
  th,td{padding:10px 8px}
  h1{font-size:23px}
  .thanh{flex-direction:column;align-items:stretch;gap:10px}
  .sub{flex:0 0 auto;width:100%}
  .nut{margin-left:0;align-self:flex-start}
  .loc{gap:10px 12px}
  .loc .dem{margin-left:0;width:100%}
  /* tren dien thoai that thi bo khung dien thoai gia di cho rong cho */
  body.dt .wrap{max-width:none}
  body.dt .tablewrap{max-width:none;border-width:1px;border-radius:12px;padding:0}
}
footer{margin-top:24px;color:var(--muted);font-size:14px;text-align:center}

/* --- xem anh phong to --- */
#lb{position:fixed;inset:0;background:rgba(0,0,0,.92);display:none;z-index:99;
  overflow:hidden;touch-action:none}
#lb.mo{display:block}
#lbimg{position:absolute;top:50%;left:50%;transform-origin:center center;
  will-change:transform;user-select:none;-webkit-user-drag:none;cursor:grab;
  max-width:none;max-height:none}
#lb.keo #lbimg{cursor:grabbing}
#lbbar{position:absolute;left:50%;bottom:22px;transform:translateX(-50%);display:flex;
  gap:6px;align-items:center;background:rgba(20,22,28,.9);border:1px solid #333a45;
  padding:7px 10px;border-radius:999px;color:#e6edf3;font-size:13px;z-index:2}
#lbbar button{background:#232833;color:#e6edf3;border:1px solid #39404d;width:32px;
  height:32px;border-radius:50%;font-size:16px;cursor:pointer;line-height:1}
#lbbar button:hover{background:#2f3644}
#lbbar .ty{min-width:52px;text-align:center;font-variant-numeric:tabular-nums}
#lbbar .dong{width:auto;padding:0 12px;border-radius:16px}
#lbcap{position:absolute;left:0;right:0;top:0;padding:14px 18px;color:#cbd5e1;
  font-size:15px;background:linear-gradient(rgba(0,0,0,.65),transparent);z-index:2}
@media print{
  body{background:#fff}
  .tablewrap{box-shadow:none}
  #lb{display:none!important}
  td.anh img{width:150px;height:84px}
}
</style>
</head>
<body>
<div class="wrap">
  <h1>__TIEUDE__</h1>
  <div class="thanh">
    <div class="sub">__PHUDE__ &middot; bấm vào ảnh để phóng to</div>
    <button type="button" class="nut" id="nutdt">📱 Xem trên điện thoại</button>
  </div>
  <div class="loc">
    <label>Từ <input type="time" id="tu"></label>
    <label>đến <input type="time" id="den"></label>
    <label>Ngày <select id="loc_ngay">__CHON_NGAY__</select></label>
    <label>Loại xe <select id="loc_loai">__CHON_LOAI__</select></label>
    <button type="button" class="xoa" id="xoaloc">Xoá lọc</button>
    <span class="dem" id="dem"></span>
  </div>
  __BANG__
  <div id="khongco">Không có lượt nào khớp bộ lọc.</div>
  <footer>__CHANTRANG__</footer>
</div>

<div id="lb">
  <div id="lbcap"></div>
  <img id="lbimg" alt="">
  <div id="lbbar">
    <button type="button" data-act="out" title="Thu nhỏ">&minus;</button>
    <span class="ty">100%</span>
    <button type="button" data-act="in" title="Phóng to">+</button>
    <button type="button" data-act="fit" title="Vừa màn hình">⤢</button>
    <button type="button" data-act="close" class="dong" title="Đóng (Esc)">Đóng</button>
  </div>
</div>

<script>
(function(){
  var tu = document.getElementById('tu'), den = document.getElementById('den'),
      loai = document.getElementById('loc_loai'), ngay = document.getElementById('loc_ngay'),
      dem = document.getElementById('dem'),
      trong = document.getElementById('khongco'),
      dong = Array.prototype.slice.call(document.querySelectorAll('tbody tr'));

  function giay(s, cuoi){
    if (!s) return null;
    var p = s.split(':');
    // o nhap chi co gio:phut -> "den 15:30" nghia la den het 15:30:59
    var gy = p.length > 2 ? +p[2] : (cuoi ? 59 : 0);
    return (+p[0]) * 3600 + (+p[1]) * 60 + gy;
  }
  function loc(){
    var a = giay(tu.value, false), b = giay(den.value, true), k = loai.value,
        n = ngay ? ngay.value : '', hien = 0;
    dong.forEach(function(tr){
      var t = giay(tr.dataset.gio, false), ok = true;
      if (a !== null && t < a) ok = false;
      if (b !== null && t > b) ok = false;
      if (k && tr.dataset.loai !== k) ok = false;
      if (n && tr.dataset.ngay !== n) ok = false;
      tr.classList.toggle('an', !ok);
      if (ok) hien++;
    });
    dem.textContent = hien + '/' + dong.length + ' lượt';
    trong.classList.toggle('hien', hien === 0);
  }
  [tu, den, loai, ngay].forEach(function(o){
    if (!o) return;
    o.addEventListener('change', loc); o.addEventListener('input', loc);
  });
  document.getElementById('xoaloc').addEventListener('click', function(){
    tu.value = ''; den.value = ''; loai.value = ''; if (ngay) ngay.value = ''; loc();
  });
  loc();
})();

(function(){
  var nut = document.getElementById('nutdt'), than = document.body;
  function ve(bat){
    than.classList.toggle('dt', bat);
    nut.textContent = bat ? '🖥️ Xem trên máy tính' : '📱 Xem trên điện thoại';
    try { localStorage.setItem('chedo_dt', bat ? '1' : '0'); } catch (e) {}
  }
  var luu = null;
  try { luu = localStorage.getItem('chedo_dt'); } catch (e) {}
  ve(luu === null ? window.innerWidth <= 760 : luu === '1');
  nut.addEventListener('click', function(){ ve(!than.classList.contains('dt')); });
})();

(function(){
  var lb = document.getElementById('lb'), im = document.getElementById('lbimg'),
      cap = document.getElementById('lbcap'), bar = document.getElementById('lbbar'),
      nhan = bar.querySelector('.ty');
  var ty = 1, x = 0, y = 0, keo = false, x0 = 0, y0 = 0, vua = 1;

  function ve(){
    im.style.transform = 'translate(-50%,-50%) translate(' + x + 'px,' + y + 'px) scale(' + ty + ')';
    nhan.textContent = Math.round(ty / vua * 100) + '%';
  }
  function fit(){
    var kx = (window.innerWidth - 60) / im.naturalWidth,
        ky = (window.innerHeight - 130) / im.naturalHeight;
    vua = Math.min(kx, ky, 1) || 1;
    ty = vua; x = 0; y = 0; ve();
  }
  function mo(src, chu){
    im.src = src; cap.textContent = chu || '';
    lb.classList.add('mo');
    if (im.complete && im.naturalWidth) { fit(); } else { im.onload = fit; }
  }
  function dong(){ lb.classList.remove('mo'); im.src = ''; }

  document.querySelectorAll('td.anh img').forEach(function(t){
    t.addEventListener('click', function(){ mo(t.dataset.full || t.src, t.dataset.chu); });
  });

  lb.addEventListener('wheel', function(e){
    e.preventDefault();
    var truoc = ty;
    ty = Math.min(vua * 12, Math.max(vua * 0.2, ty * (e.deltaY < 0 ? 1.15 : 1 / 1.15)));
    // giu diem duoi con tro dung yen khi phong to
    var cx = e.clientX - window.innerWidth / 2, cy = e.clientY - window.innerHeight / 2;
    x = cx - (cx - x) * (ty / truoc);
    y = cy - (cy - y) * (ty / truoc);
    ve();
  }, {passive:false});

  im.addEventListener('pointerdown', function(e){
    keo = true; x0 = e.clientX - x; y0 = e.clientY - y;
    lb.classList.add('keo'); im.setPointerCapture(e.pointerId);
  });
  im.addEventListener('pointermove', function(e){
    if (!keo) return;
    x = e.clientX - x0; y = e.clientY - y0; ve();
  });
  im.addEventListener('pointerup', function(){ keo = false; lb.classList.remove('keo'); });
  im.addEventListener('dblclick', function(){
    ty = (ty > vua * 1.2) ? vua : vua * 2.5; x = 0; y = 0; ve();
  });

  bar.addEventListener('click', function(e){
    var a = e.target.getAttribute('data-act');
    if (!a) return;
    if (a === 'in')  { ty = Math.min(vua * 12, ty * 1.3); ve(); }
    if (a === 'out') { ty = Math.max(vua * 0.2, ty / 1.3); ve(); }
    if (a === 'fit') { fit(); }
    if (a === 'close') { dong(); }
  });
  lb.addEventListener('click', function(e){ if (e.target === lb) dong(); });
  document.addEventListener('keydown', function(e){
    if (!lb.classList.contains('mo')) return;
    if (e.key === 'Escape') dong();
    if (e.key === '+' || e.key === '=') { ty = Math.min(vua * 12, ty * 1.3); ve(); }
    if (e.key === '-') { ty = Math.max(vua * 0.2, ty / 1.3); ve(); }
    if (e.key === '0') fit();
  });
  window.addEventListener('resize', function(){ if (lb.classList.contains('mo')) fit(); });
})();
</script>
</body>
</html>
"""


def _esc(s):
    if s is None:
        s = u""
    if not isinstance(s, str):
        s = str(s)
    return html.escape(s)


def _bang(events, prefix=""):
    if not events:
        return u'<div class="tablewrap"><div class="empty">Chưa ghi nhận lượt xe nào.</div></div>'
    rows = []
    # Moi NGAY danh so lai tu 1: bao cao gop nhieu ngay, ma nguoi xem
    # thuong loc theo tung ngay nen so thu tu chay tiep tu ngay truoc
    # (ngay 25 bat dau tu 17...) doc rat kho hieu.
    dem_ngay = {}
    for e in events:
        ngay_e = e.get("thoi_gian", "")[:10]
        dem_ngay[ngay_e] = dem_ngay.get(ngay_e, 0) + 1
        i = dem_ngay[ngay_e]
        # Khong phan biet loai xe nua - moi luot deu la "Phuong tien".
        loai, cls, ten = u"vehicle", u"vehicle", VI[u"vehicle"]

        gio = _esc(e.get("thoi_gian", ""))
        if e.get("thoi_gian_chac_chan") is False:
            gio += u' <span class="uoc" title="Mốc giờ đọc tự động, nên đối chiếu lại">≈</span>'

        pfx = e.get("_pfx", prefix)
        thumb = e.get("anh_danh_dau") or e.get("anh")
        full = e.get("anh") or thumb
        chu = u"%s · %s · %s" % (e.get("ma_luot", ""), ten, e.get("thoi_gian", ""))
        anh = (u'<img loading="lazy" src="%s%s" data-full="%s%s" data-chu="%s" alt="%s">'
               % (pfx, _esc(thumb), pfx, _esc(full), _esc(chu), _esc(chu)))

        rows.append(
            u'<tr data-gio="%s" data-ngay="%s" data-loai="%s">'
            u'<td class="stt">%d</td><td class="gio">%s</td>'
            u'<td class="loai"><span class="pill %s">%s</span></td>'
            u'<td class="anh">%s</td></tr>'
            % (_esc(e.get("thoi_gian", "")[11:]), _esc(e.get("thoi_gian", "")[:10]),
               _esc(loai), i, gio, cls, _esc(ten), anh)
        )
    return (u'<div class="tablewrap"><table><thead><tr>'
            u"<th>STT</th><th>Thời gian</th><th>Loại xe</th><th>Hình ảnh</th>"
            u"</tr></thead><tbody>%s</tbody></table></div>" % _NL.join(rows))


def _chon_loai(events):
    """O loc 'Loai xe' - gio chi con mot loai duy nhat la 'Phuong tien'."""
    if not events:
        return u'<option value="">Tất cả</option>'
    return (u'<option value="">Tất cả</option>'
            u'<option value="vehicle">%s</option>' % _esc(VI[u"vehicle"]))


def build(session_id, out_path=None):
    """Sinh bao cao HTML cho mot phien. Tra ve duong dan file."""
    data = storage.load_session(session_id)
    meta = data.get("phien", {})
    events = data.get("su_kien", [])

    os.makedirs(REPORT_DIR, exist_ok=True)
    if out_path is None:
        out_path = os.path.join(REPORT_DIR, u"BaoCao_%s.html" % session_id)

    rel = os.path.relpath(
        os.path.join(storage.CAPTURE_DIR, session_id), os.path.dirname(out_path)
    ).replace("\\", "/")
    prefix = rel + "/"

    ngay = (meta.get("bat_dau") or "")[:10]
    phude = u"%s &middot; %s lượt" % (_esc(meta.get("camera", u"Camera")), len(events))
    if ngay:
        phude += u" &middot; ngày %s" % _esc(u"-".join(reversed(ngay.split("-"))))

    out = TEMPLATE
    for k, v in {
        "__TIEUDE__": _esc(u"Danh sách xe ghi nhận"),
        "__PHUDE__": phude,
        "__BANG__": _bang(events, prefix),
        "__CHON_LOAI__": _chon_loai(events),
        "__CHON_NGAY__": _chon_ngay(events),
        "__CHANTRANG__": _esc(
            u"Phiên %s · xuất lúc %s"
            % (meta.get("ma_phien", session_id),
               datetime.now().strftime("%d-%m-%Y %H:%M"))),
    }.items():
        out = out.replace(k, v)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return out_path


# ---------------------------------------------------------------- gop nhieu ngay
def _chon_ngay(events):
    """Danh sach lua chon cho o loc 'Ngay'.

    Mac dinh chon NGAY MOI NHAT: mo bao cao len la thay ngay hom nay ngay,
    khong phai cuon qua ca nhung ngay cu. Bam "Xoa loc" de xem lai tat ca.
    """
    ngays = sorted({e.get("thoi_gian", "")[:10] for e in events if e.get("thoi_gian")},
                   reverse=True)
    out = [u'<option value="">Tất cả</option>']
    for i, n in enumerate(ngays):
        out.append(u'<option value="%s"%s>%s</option>'
                   % (_esc(n), u" selected" if i == 0 else u"",
                      _esc(u"-".join(reversed(n.split("-"))))))
    return u"".join(out)


def gom_su_kien(out_dir, gioi_han_ngay=None):
    """Gop su kien cua tat ca cac phien lai. Moi su kien mang duong dan anh rieng."""
    goi = []
    for sid in storage.list_sessions():
        try:
            data = storage.load_session(sid)
        except Exception:
            continue
        pfx = os.path.relpath(os.path.join(storage.CAPTURE_DIR, sid),
                              out_dir).replace("\\", "/") + "/"
        cam = data.get("phien", {}).get("camera", "")
        for e in data.get("su_kien", []):
            e = dict(e)
            e["_pfx"] = pfx
            e["_camera"] = cam
            goi.append(e)
    goi.sort(key=lambda e: e.get("thoi_gian", ""))     # som nhat len dau

    if gioi_han_ngay:
        giu = set(sorted({e.get("thoi_gian", "")[:10] for e in goi},
                         reverse=True)[:gioi_han_ngay])
        goi = [e for e in goi if e.get("thoi_gian", "")[:10] in giu]
    return goi


def build_all(out_path=None, gioi_han_ngay=None):
    """Sinh MOT bao cao gop tat ca cac ngay. Tra ve (duong dan, so luot, so ngay)."""
    out_path = out_path or os.path.join(ROOT, "index.html")
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    events = gom_su_kien(os.path.dirname(out_path) or ROOT, gioi_han_ngay)

    ngays = sorted({e.get("thoi_gian", "")[:10] for e in events if e.get("thoi_gian")})
    dem_cam = Counter(e.get("_camera", "") for e in events if e.get("_camera"))
    cam = dem_cam.most_common(1)[0][0] if dem_cam else u"Camera"
    cam = cam.split(u"–")[0].strip() or cam        # bo phan "- ban ghi ..." neu co
    phude = u"%s &middot; %d lượt &middot; %d ngày" % (_esc(cam), len(events), len(ngays))
    if ngays:
        dau = u"-".join(reversed(ngays[0].split("-")))
        cuoi = u"-".join(reversed(ngays[-1].split("-")))
        phude += u" (%s)" % (dau if dau == cuoi else u"%s → %s" % (dau, cuoi))
    if gioi_han_ngay:
        phude += u" &middot; %d ngày gần nhất" % gioi_han_ngay

    out = TEMPLATE
    for k, v in {
        "__TIEUDE__": _esc(u"Danh sách xe ra vào mỏ"),
        "__PHUDE__": phude,
        "__BANG__": _bang(events),
        "__CHON_LOAI__": _chon_loai(events),
        "__CHON_NGAY__": _chon_ngay(events),
        "__CHANTRANG__": _esc(u"Cập nhật lúc %s"
                              % datetime.now().strftime("%d-%m-%Y %H:%M")),
    }.items():
        out = out.replace(k, v)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(out)
    return out_path, len(events), len(ngays)


NGAY_TREN_WEB = 3          # so ngay gan nhat duoc dua len GitHub


def sinh_bao_cao(log=None):
    """Sinh ca hai ban: ban dua len web (3 ngay gan nhat) va ban day du o may."""
    noi = log or (lambda *_a: None)
    web, n1, d1 = build_all(os.path.join(ROOT, "index.html"),
                            gioi_han_ngay=NGAY_TREN_WEB)
    noi(u"Báo cáo web (%d ngày gần nhất): %d lượt – %s" % (NGAY_TREN_WEB, n1, web))
    day_du, n2, d2 = build_all(os.path.join(REPORT_DIR, "BaoCao_toan_bo.html"))
    noi(u"Báo cáo đầy đủ tại máy (%d ngày): %d lượt – %s" % (d2, n2, day_du))
    return web, day_du
