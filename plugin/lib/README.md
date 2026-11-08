# lib/ — thu muc chua thu vien API cua CSI (du phong)

Project Plugin tham chieu `ETABSv1.dll` theo thu tu uu tien:

1. **Duong dan cai dat ETABS tren may** (mac dinh, khong can copy):
   `C:\Program Files\Computers and Structures\ETABS 22\ETABSv1.dll`
2. **Ban copy trong thu muc nay** (`lib/ETABSv1.dll`) — chi dung khi may
   build khong co ETABS (vd may dev Linux dung de kiem tra bien dich).

File `CSiAPIv1.dll` trong thu muc nay (neu co) CHI DE THAM CHIEU —
ban .NET 8 truoc day dung no, ban net48 hien tai dung `ETABSv1.dll`.

Cac file nay KHONG co trong repo (nhi phân cua CSI — `.gitignore` chan
`lib/*.dll`) va KHONG duoc dong goi kem khi phat hanh plugin:
luc chay, ETABS da nap san API nay.
