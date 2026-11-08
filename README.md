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

- **Đã validate trên file thật 2026-11-08**: ban vẽ PDF
  `BANG_NOI_LUC_0_qo1t.pdf` (3 tờ A0, SH.4/5/6) đã chuyển thành
  `examples/BANG_NOI_LUC_BC-5A_B.xlsx` — 17 bảng, 183 điểm, 321 dòng,
  10.908 ô (OCR + đối chiếu bằng mắt từng ô khả nghi). Detector đọc
  khớp 17/17 sheet; test `tests/test_real_excel.py` (19 test) chạy trên
  file thật này. File PDF gốc (20MB, nhị phân) không đẩy lên GitHub
  được — giữ ở `tests/fixtures/` local.
- **Chưa test trên ETABS thật**: tên hàm COM (`PointObj.SetLoadForce`,
  `LoadPatterns.Add`, `SelectObj.GetSelected`) và mã enum loại pattern
  **đã đối chiếu trực tiếp với `CSiAPIv1.dll` thật từ ETABS v22**
  (2026-11-08) — nhưng chưa gọi lần nào trên model sống. Nếu hàm nào báo
  lỗi trên máy thật, ghi lại thông báo + version ETABS để sửa.
- **Gợi ý match pattern chưa được bạn xác nhận** (BC1=BC-5A, BT1=belt
  tension, NX/NY=Imperfektion... suy từ tên gọi). Kiểm tra bảng match
  trước khi gán.
- Chỉ gán tải điểm (point load) tại joint — chưa gán tải lên frame/area,
  chưa tạo load case/combo.

## File thật — BẢNG NỘI LỰC LONG PHU BC-5 (2026-11-08)

File Excel `examples/BANG_NOI_LUC_BC-5A_B.xlsx` chuyển từ bản vẽ PDF thật
`BANG_NOI_LUC_0_qo1t.pdf` (FOUNDATION & LOADS SH.4/5/6, LONG PHU-1):
17 bảng, 183 điểm, 321 dòng tải, 10.908 ô số — OCR (RapidOCR + OpenCV)
+ đối chiếu bằng mắt từng ô khả nghi (xem `pdf_to_excel/` — script OCR,
sửa tay có ghi chú). Mỗi bảng 1 sheet (tên SH4-T1...), chọn sheet ở
thanh trên trước khi nhấn diện. Sheet `KIEM TRA` trong file Excel liệt
kê các ô đã sửa tay + ghi chú (vd ô `+/- 1` ở bảng 90/D.1, khoang
`67/-71` ở bảng 85.1).

## Thay đổi v0.1.1 (đã push, head `609cb8c`)

- Chọn sheet khi file Excel có nhiều bảng (combobox ở thanh trên).
- `detector.parse_cell`: ô viết `+/- 1` (bảng 90/D.1) parse ra 1.
- `Profile.pattern_for`: match pattern không phân biệt hoa/thường —
  profile ví dụ lưu key chữ thường, trước đây assigner bỏ qua toàn bộ
  dòng vì không khớp tên (lỗi tìm được nhờ test trên file thật).

## Thay đổi v0.1.2 (đang push)

- **Hàng ± gán cả 2 chiều (user chốt)**: `reversible_mode="both"` mặc định
  (app + profile ví dụ) — pattern gốc + pattern `_NEG` đảo dấu.
- **Tự tạo pattern thiếu, đúng loại**: tick "Tự tạo pattern..." mặc định BẬT;
  pattern `_NEG` kế thừa loại của pattern gốc (`EX_NEG` <- `EX` Seismic,
  `NX_NEG` <- `NX` Notional, `T_NEG` <- `T` Temperature) qua
  `etabs_api.create_type_for()`; fallback Other=8 nếu `Add` lỗi.
- **Sửa mã loại pattern (đối chiếu `CSiAPIv1.dll` thật, ETABS v22)**:
  Notional=12 (bản cũ ghi 9 — 9 là Move!), Rooflive=11 (bản cũ 4 =
  ReduceLive), Temperature=10 (bản cũ 8).
- **Sửa 3 lỗi chữ ký `RealEtabs` (đối chiếu DLL thật)**: `GetLoadType`
  chỉ trả 1 out, `GetLabelFromName` chỉ 2 out, thuộc tính đúng là
  `SelectObj` (không phải `Select`).
- Test: 30/30 pass (9 cũ + 19 file thật + 2 mới cho auto-create `_NEG`).
