# ETABS Load Assigner — Plugin trong ETABS

> **Lưu ý 2026-11-08:** Plugin C# (DLL riêng) đã gộp vào **Etabs Ultimate Tools** (tab "Load Assigner", repo `ndkhoams/Etabs_Plugin`, head `342b028`) — DLL riêng bị ETABS báo "Not Found" khi Add (nguyên nhân chưa rõ) nên không còn duy trì. App Python (`app.py`) giữ nguyên, không phát triển thêm (quyết 08/11). Hướng dẫn dưới đây chỉ còn giá trị tham khảo cho code đã gộp.

Gán tải móng từ file Excel (bảng Foundation loads LONG PHU BC-5) vào model
ETABS đang mở, chạy **trong ETABS** qua menu Tools — không phải app chạy ngoài.

## Target — đã khóa

- **ETABS v22, .NET Framework 4.8 + `ETABSv1.DLL`** — build theo đúng kiểu
  Ultimate Tools (repo `Etabs_Plugin`), vì bản .NET 8 + `CSiAPIv1.DLL`
  trước đây bị ETABS báo "Not Found" khi Add (đường dẫn đúng, file đúng,
  mô phỏng nạp OK) nên đã bỏ hẳn từ 2026-11-08.
- File `ETABSv1.dll` lấy từ **thư mục cài ETABS trên máy user**
  (vd `C:\Program Files\Computers and Structures\ETABS 22\`) — project
  trỏ thẳng tới đó, không cần chép đi đâu (fallback `lib/` nếu máy
  không có ETABS). File này **KHÔNG có trong repo**
  (nhị phân của CSI, `.gitignore` đã chặn `lib/*.dll`), và cũng
  **KHÔNG đóng gói kèm DLL phát hành** (lúc chạy, ETABS đã nạp sẵn API này).

## Build

```bash
# 1. (Khong can chep DLL — project tro thang toi thu muc cai ETABS;
#    chi khi may khong co ETABS moi can ETABSv1.dll trong lib/)
# 2. Build (can .NET 8 SDK de build net48 tren Linux, hoac VS 2022 tren Windows)
dotnet build EtabsLoadAssigner.sln -c Release
# 3. Lay file: src/EtabsLoadAssigner.Plugin/bin/Release/
#    EtabsLoadAssignerPlugin.dll + EtabsLoadAssigner.Core.dll + ClosedXML.dll
#    (+ DocumentFormat.OpenXml.dll...) — de TAT CA cung 1 thu muc khi nap
#    vao ETABS (ETABSv1.dll KHONG co trong do — ETABS nap san).
```

Build trên Linux chỉ để kiểm tra biên dịch (cần file `ETABSv1.dll` thật
trong `lib/` + PackageReference `Microsoft.NETFramework.ReferenceAssemblies`
trên bản sao — xem AGENTS.md repo `Etabs_Plugin`); DLL chạy thật vẫn cần
Windows + ETABS.

## Cài đặt trong ETABS

1. Mở ETABS (model cần gán tải).
2. **Tools > Add/Show Plug-Ins...** > Browse tới `EtabsLoadAssignerPlugin.dll` > Add.
3. Chạy bằng **Tools > ETABS Load Assigner**.

## Sử dụng (5 tab, như app Python)

1. **File & bảng** — Chọn file Excel `.xlsx` (mỗi bảng 1 sheet, chọn sheet
   ở thanh trên) > Nhận diện bảng. Plugin **không đọc PDF** — file PDF bản
   vẽ scan phải chuyển sang Excel trước (script `pdf_to_excel/` ở repo
   app Python).
2. **Điểm gán tải** — Chọn điểm Excel, sửa alias điểm -> joint ETABS nếu
   tên joint trong model khác. Nút "Lấy điểm đang chọn trong ETABS" đọc
   joint đang chọn trong model.
3. **Phương & chiều** — Map Hx/Hy/Vz sang trục ETABS. Mặc định Hx->+X,
   Hy->+Y, **Vz->-Z** (bản vẽ "+z down", ETABS +Z hướng lên).
4. **Match pattern** — Gán từng dòng Excel sang pattern ETABS (gợi ý theo
   tên chỉ là gợi ý, bạn chốt lại). Tick "Tự tạo pattern..." để plugin tự
   tạo pattern chưa có trong model.
5. **Preview & gán** — Xem trước rồi bấm **GÁN VÀO ETABS**
   (`PointObj.SetLoadForce`, đơn vị kN, M = 0 vì bảng gốc chỉ có lực).

Cài đặt (axis, pattern, alias) lưu ra
`%AppData%\EtabsLoadAssigner\profile.json` và tự tải lại lần sau
(vì ETABS hủy đối tượng plugin giữa các lần gọi từ menu Tools).

## Quy ước mặc định

- Ô khoang `-3/+6`: lấy giá trị có `|.|` lớn nhất (`range_policy=max_abs`).
- **Hàng ± gán CẢ 2 chiều (user chốt 08/11):** pattern gốc + pattern `_NEG`
  đảo dấu (vd `EX` và `EX_NEG`), `reversible_mode="both"` mặc định.
  Plugin cảnh báo rõ khi tạo `_NEG` — nhớ kiểm tra pattern `_NEG` có
  trong model không (hoặc tick "Tự tạo pattern...").
- **Tự tạo pattern thiếu (user chốt 08/11):** tick "Tự tạo pattern..."
  (mặc định BẬT) thì pattern nào thiếu sẽ tự tạo trong model trước khi gán.
  Pattern `_NEG` kế thừa **đúng loại của pattern gốc** (`EX_NEG` <- `EX`
  Seismic, `NX_NEG` <- `NX` Notional, `WX+_NEG` <- `WX+` Wind,
  `T_NEG` <- `T` Temperature=10);
  pattern khác hoặc không tìm thấy gốc -> Other. Nếu `Add` lỗi thì tự
  fallback về Other=8.
  LƯU Ý: mã loại lấy theo enum `eLoadPatternType` (đã verify trên file
  `CSiAPIv1.dll` thật; `ETABSv1.dll` dùng chung API — sẽ xác minh lại
  khi có file) — bản
  Python cũ ghi sai 3 mã (Notional=9, Rooflive=4, Temperature=8),
  **đã sửa cả 2 bên ngày 08/11** sau khi đọc enum trực tiếp từ DLL.
- Hàng toàn 0 bị bỏ qua (`skip_zero_rows=true`).
- Ghi đè tải cũ cùng pattern tại điểm đó (`replace_existing=true`).

## Cấu trúc repo

```
EtabsLoadAssigner.sln
src/EtabsLoadAssigner.Core/      netstandard2.0, KHONG phu thuoc CSI DLL
  Detector.cs                    nhan dien bang tu .xlsx (ClosedXML)
  Mapping.cs                     AxisMapping, Profile, suggest_pattern
  Assigner.cs                    build_assignments + preview
  EtabsApi.cs                    IEtabsApi + MockEtabs (test offline)
                                 + PatternTypes (create_type_for / ma loai)
src/EtabsLoadAssigner.Plugin/    net48 (WinForms) — theo kieu Ultimate Tools
  cPlugin.cs                     cPlugin (chi Main, khong Info/contract)
  RealEtabs.cs                   IEtabsApi tren SapModel song (ETABSv1)
  MainForm.cs                    UI 5 tab
tests/EtabsLoadAssigner.Core.Tests/   xUnit (net8.0) — chay tren fixture tong hop
lib/                             ETABSv1.dll (fallback) + CSiAPIv1.dll (tham chieu)
                                 — KHONG co trong repo, xem lib/README.md
examples/profile_longphu_example.json   profile vi du (LONG PHU BC-5)
```

## Trạng thái kiểm chứng — đọc trước khi dùng trên model thật

- **Core (netstandard2.0) + test: build OK 0 warning / 0 error, test 21/21 pass**
  (2026-11-08, sau khi chuyển từ net8.0 sang netstandard2.0 để dùng chung
  với Plugin net48; chỉ sửa 4 chỗ tương thích API: Substring thay `..`/`^`,
  `.Cast<Match>()` cho `MatchCollection`, bỏ deconstruct `KeyValuePair`).
- **Plugin (net48): CHƯA build xong — đang chờ file `ETABSv1.dll` thật**
  từ máy user để build kiểm chứng (project trỏ tới đường dẫn cài ETABS,
  fallback `lib/ETABSv1.dll`). Build trên Linux cần thêm
  `Microsoft.NETFramework.ReferenceAssemblies` trên bản sao (xem AGENTS.md
  repo `Etabs_Plugin`).
- **Test: 21/21 pass** (6 Detector + 15 Assigner, gồm 4 test mới cho
  auto-create `_NEG`: `CreateTypeFor_InheritsBaseType`,
  `CreateTypeFor_TypeToCode`, `MockEtabs_CreatePattern_WithTypeCode`,
  `MockAssign_AutoCreateNegPatterns_ThenAssignAll`).
  LƯU Ý: `dotnet test` (vstest) **không chạy được trên VM Linux dev này**
  — testhost khởi động nhưng không bao giờ bắt tay xong (thử 3 lần, timeout
  90/300/600s đều abort; loopback vẫn OK, có thể do VM thiếu RAM/tràn swap).
  21 test trên được chạy trực tiếp bằng 1 console runner nhỏ (load DLL test
  đã build, gọi từng `[Fact]` với instance mới + Dispose như xUnit),
  21/21 pass trong ~3s. Trên máy Windows của user, `dotnet test` chạy bình
  thường — nên chạy lại 1 lần để lấy log chuẩn.
  Test chạy trên **fixture tổng hợp** chép tay từ ảnh — bằng chứng yếu;
  parity với file Excel thật đã chạy riêng (17 bảng / 183 điểm / 321 dòng,
  khớp từng chữ số với app Python): điểm 20/D bảng SH4-T1 ra đúng
  18 assignment; **tự tạo đúng 6 pattern `_NEG`** (EX/EY/EZ_NEG Seismic,
  NX/NY_NEG Notional, T_NEG Temperature) rồi gán đủ 18 tải — **PARITY: ALL PASS**.
- **Plugin DLL (bản net48) chưa build xong — đang chờ `ETABSv1.dll` thật**,
  và **chưa từng chạy trong ETABS thật**: `SetLoadForce`, `GetSelected`,
  `GetAllPoints`... chưa gọi lần nào trên model sống.
- Đã đối chiếu chữ ký hàm với file DLL thật (không đoán theo bản Python),
  và **bản Python đã sửa theo ngày 08/11** (3 lỗi chữ ký + 3 mã loại):
  - `LoadPatterns.GetLoadType` chỉ trả về `MyType` (bản Python cũ unpack 4 giá trị
    — lỗi bị `except` nuốt nên type pattern luôn rỗng, `_NEG` sẽ toàn về Other).
  - `PointObj.GetLabelFromName(Name, ref Label, ref Story)` — chỉ 2 out
    (bản Python cũ unpack 4 — lỗi bị nuốt, label rớt về tên joint).
  - Mã loại pattern `eLoadPatternType`: `Rooflive=11` (Python ghi 4),
    `Temperature=10` (Python ghi 8), `Notional=12` (Python ghi 9);
    `SetLoadForce(..., Replace)` mặc định là **False** — code luôn truyền rõ.
  - `SapModel.SelectObj` (không phải `.Select` như comtypes gọi tắt —
    bản Python cũ sẽ crash khi lấy điểm đang chọn).
- **BẮT BUỘC trước khi gán hàng loạt:** kiểm dấu 1 điểm thật (gán chỉ DLS
  ở 1 joint, xem Fz có âm không) theo `HUONG_DAN_TEST.md` mục 1 ở repo app
  Python. Gợi ý match pattern (BC1=BC-5A, BT1=belt tension, NX/NY=...) chỉ
  suy từ tên, chưa được user xác nhận.
