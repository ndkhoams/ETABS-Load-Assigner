# lib/ — thu muc chua thu vien API cua CSI (du phong)

Project Plugin tham chieu `CSiAPIv1.dll` theo thu tu uu tien:

1. **Duong dan cai dat ETABS tren may** (mac dinh, khong can copy):
   `C:\Program Files\Computers and Structures\ETABS 22\CSiAPIv1.dll`
2. **Ban copy trong thu muc nay** (`lib/CSiAPIv1.dll`) — chi dung khi may
   build khong co ETABS (vd may dev Linux dung de kiem tra bien dich).

File nay KHONG co trong repo (nhi phân cua CSI — `.gitignore` chan
`lib/*.dll`) va KHONG duoc dong goi kem khi phat hanh plugin:
luc chay, ETABS da nap san API nay.
