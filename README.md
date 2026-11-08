# ETABS Load Assigner v0.1

Gán tải móng (foundation loads) từ file Excel/PDF của client vào ETABS,
tự động — thay cho gán tay từng pattern từng điểm.

## 5 chức năng (theo yêu cầu)

1. **Chọn điểm gán tải** — tab 2: chọn điểm Excel (vd `20 / D`), ánh xạ
   sang joint ETABS (mặc định cùng tên, sửa được), hoặc lấy joint đang
   chọn trong model ETABS.
2. **Phương & chiều** — tab 3: mỗi trục Excel (Hx, Hy, Vz) ánh xạ sang
   trục global ETABS (X/Y/Z) + dấu +/−. Mặc định: `Hx -> +X, Hy -> +Y,
   Vz -> -Z` (vì sơ đồ gốc ghi "+z down", ETABS +Z hướng lên).
   **Dấu Hx/Hy không suy ra được từ ảnh — phải kiểm 1 điểm thật trước
   khi gán hàng loạt** (xem `HUONG_DAN_TEST.md` mục 4).
3. **Bảng match pattern** — tab 4: từng dòng tải Excel <-> pattern ETABS
   (dropdown, có gợi ý tự động theo tên — chỉ là gợi ý, bạn chốt lại).
   Pattern chưa có trong model: báo lỗi, hoặc tick "Tự tạo pattern".
4. **Lưu cài đặt** — nút "Lưu profile..." (JSON): lưu axis mapping,
   pattern map, point alias, các tùy chọn. Lần sau "Tải profile...",
   chỉ đổi điểm gán.
5. **Tự động nhận diện bảng** — tab 1: import `.xlsx` hoặc `.pdf`,
   app tự tìm bảng `Foundation loads` (cụm Hx/Hy/Vz, mỗi điểm 3 cột)
   và bảng `Load Pattern Definitions` (Name/Type/GUID). Cùng một hàm
   nhận diện cho cả Excel lẫn PDF.

## Quy tắc xử lý các ô đặc biệt (ghi rõ, không giấu)

- Ô khoang `-3/+6`: mặc định lấy giá trị có |.| lớn nhất (+6), ghi chú
  trong preview. Đổi được: max / min / bỏ qua (tab 4).
- Hàng `+/-` (Imperfektion, Friction, Temperatur, Earthquake...):
  mặc định chỉ gán chiều + như trong bảng; chọn `both` để tạo thêm
  pattern `_NEG` chiều âm.
- Hàng toàn 0: bỏ qua (ghi trong preview), không gán tải 0 vào model.
- Bảng gốc chỉ có lực (Hx, Hy, Vz) — không có moment: Mx = My = Mz = 0.
- Đơn vị: kN (theo `[kN]` trong bảng). App đặt `SetPresentUnits(6)`
  = kN_m_C khi truyền qua API.

## Chạy

```bash
pip install -r requirements.txt
python -m pytest tests/ -q   # 9 test pass (fixture tổng hợp)
python main.py
```

Build .exe trên Windows: `pip install pyinstaller` rồi `python build_exe.py`
-> `dist/ETABSLoadAssigner.exe`.

## Cấu trúc

- `etabs_loader/detector.py` — nhận diện bảng Excel/PDF
- `etabs_loader/mapping.py` — axis mapping, gợi ý pattern, profile JSON
- `etabs_loader/assigner.py` — build danh sách gán + preview
- `etabs_loader/etabs_api.py` — ETABS COM (comtypes) + Mock offline
- `etabs_loader/app.py` — giao diện Tkinter (5 tab)
- `examples/` — fixture tổng hợp LONG PHU BC-5 + profile ví dụ
- `tests/` — test detector/assigner/mock/profile/PDF

## Giới hạn v0.1 — đọc trước khi dùng trên model thật

- **Chưa test trên file thật**: detector mới chỉ chạy trên fixture tổng
  hợp chép tay từ ảnh screenshot. File Excel/PDF thật (LP1-PB19-10EAC-...)
  có thể khác layout (sheet khác, dòng header khác) — gửi file thật để
  validate lại detector.
- **Chưa test trên ETABS thật**: tên hàm COM (`PointObj.SetLoadForce`,
  `LoadPatterns.Add`, `Select.GetSelected`) lấy từ hướng dẫn API công
  khai; mã enum loại pattern (trừ Other=8) chưa đối chiếu file
  `CSI API ETABS v1.chm`. Nếu hàm nào báo lỗi trên máy thật, ghi lại
  thông báo + version ETABS để sửa theo đúng .chm.
- **Gợi ý match pattern chưa được bạn xác nhận** (BC1=BC-5A, BT1=belt
  tension, NX/NY=Imperfektion... suy từ tên gọi). Kiểm tra bảng match
  trước khi gán.
- Chỉ gán tải điểm (point load) tại joint — chưa gán tải lên frame/area,
  chưa tạo load case/combo.
