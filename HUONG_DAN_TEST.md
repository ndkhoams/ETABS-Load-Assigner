# Hướng dẫn test ETABS Load Assigner v0.1

## 0. Thử nhanh không cần ETABS (5 phút, máy nào cũng được)

```bash
pip install -r requirements.txt
python -m pytest tests/ -q   # 9 test pass
python main.py
```

Trong app (chế độ Offline — Mock ETABS):
1. "Chọn file Excel/PDF..." -> `examples/longphu_bc5_synthetic.xlsx` -> "Nhận diện bảng".
   Phải ra: **4 điểm (20/D, 20/E, 27/D, 27/E), 26 dòng tải, 29 pattern**.
2. Tab 2: điểm `20 / D`. Tab 3: giữ mặc định `Hx->+X, Hy->+Y, Vz->-Z`.
3. Tab 4: bấm "Gợi ý tự động tất cả" (Dead loads -> DLS, Wind +X -> WX+...).
4. Tab 5: "Xem preview". Kiểm tra 3 số này:
   - `DLS: Fx=0, Fy=-2, Fz=-19` (Dead loads 20/D: Hy=-2, Vz=19 xuống -> Fz âm)
   - `WY+1: Fy=7, Fz=+11` (Wind +Y: Hy=7, Vz=-11 -> Fz=+11)
   - `WY-1: Fz=-6` (ô khoang `-3/+6` -> lấy +6 theo |.| lớn nhất)
5. "GÁN VÀO ETABS" (mock): báo đã gán, không cần ETABS thật.

## 1. Kiểm dấu — BẮT BUỘC, làm 1 lần trước khi gán hàng loạt (5 phút)

Dấu Vz đã chắc (sơ đồ gốc ghi "+z down", ETABS +Z lên -> Vz -> -Z).
Dấu Hx/Hy thì **chưa chắc** — ảnh chỉ vẽ mũi tên, không nói trùng
hướng +X/+Y của model ETABS hay ngược lại.

1. Mở model ETABS thật, chọn 1 joint móng rõ ràng (vd chân cột chịu
   Dead loads Vz=19 kN xuống, Hy=-2).
2. Trong app: chuyển sang "ETABS thật đang mở" -> "Kết nối ETABS",
   chọn điểm đó, gán **chỉ 1 pattern DLS** (bỏ match các dòng khác tạm).
3. Trong ETABS: Display > Load Assigns > Joint Loads, xem joint đó:
   - Fz phải **âm** (-19). Nếu Fz = +19: đổi Vz -> +Z trong tab 3.
   - Fy phải **-2**. Nếu Fy = +2: đổi Hy -> -Y.
   - Fx kiểm tương tự với 1 dòng có Hx != 0 (vd Wind +X, Hx=1).
4. Khi dấu đã đúng, **Lưu profile** ngay — từ đó gán các điểm sau
   không cần kiểm lại.

## 2. Test trên ETABS thật — gán 1 điểm rồi đối chiếu

1. Kết nối ETABS đang mở (model đã có đủ 29 pattern như bảng phải).
2. Import file Excel thật (chưa có thì dùng file fixture ở mục 0).
3. Tab 4: kiểm tra **từng dòng match** — đặc biệt các dòng gợi ý
   tự động (BC1/BC2, BT1/BT2, SLL/SPL, LL1-LL5) vì gợi ý chỉ suy
   từ tên gọi, chưa được bạn xác nhận.
4. Tab 5: preview, rồi gán điểm `20 / D`.
5. Đối chiếu trong ETABS (Joint Loads) 3-5 pattern ngẫu nhiên với
   preview trong app — phải khớp từng số.
6. Nếu ETABS báo thiếu pattern: hoặc tạo tay trong ETABS rồi gán lại,
   hoặc tick "Tự tạo pattern chưa có trong model" ở tab 4 rồi gán lại.

## 3. Gán điểm mới bằng profile đã lưu (luồng dùng hàng ngày)

1. Mở app -> "Tải profile..." -> chọn file `.json` đã lưu ở mục 1.
2. Import file Excel (cùng file hoặc file mới cùng dạng bảng).
3. Tab 2: đổi điểm (vd `27 / D`) — mọi mapping giữ nguyên.
4. Tab 5: preview -> gán. Không cần làm lại tab 3, tab 4.

## 4. Nếu gặp lỗi COM trên ETABS thật

- Ghi lại **nguyên văn thông báo lỗi + version ETABS** (vd 21, 22...).
- Mở file `C:\Program Files\Computers and Structures\ETABS <version>\CSI API ETABS v1.chm`,
  tra tên hàm báo lỗi (`PointObj.SetLoadForce`, `LoadPatterns.Add`,
  `Select.GetSelected`) — tên hàm trong `etabs_loader/etabs_api.py`
  cần sửa theo đúng .chm đó.
- Riêng mã loại pattern khi "Tự tạo pattern": app thử mã theo tên
  loại, nếu lỗi sẽ tự fallback về Other (8). Nếu vẫn lỗi, tạo
  pattern tay trong ETABS rồi bỏ tick tự tạo.

## 5. Gửi lại để validate detector trên file thật

Gửi file Excel/PDF gốc (tab `LP1-PB19-10EAC-C-M2...` trong ảnh) —
app sẽ chạy detector trên file thật và báo: số điểm/dòng/pattern
đọc được, dòng nào lệch so với ảnh. Đó mới là test quyết định
cho chức năng 5; test trên fixture tổng hợp chỉ chứng minh logic
chạy đúng với dạng bảng trong ảnh.
