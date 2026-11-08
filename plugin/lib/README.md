# lib/ — thu muc chua thu vien API cua CSI

Chep file `CSiAPIv1.dll` tu thu muc cai ETABS v22 tren may ban vao day
truoc khi build, vd:

    C:\Program Files\Computers and Structures\ETABS 22\CSiAPIv1.dll

File nay KHONG co trong repo (nhi phân cua CSI — `.gitignore` chan
`lib/*.dll`) va KHONG duoc dong goi kem khi phat hanh plugin:
luc chay, ETABS da nap san API nay.

Project Plugin tham chieu toi file nay qua
`<Reference HintPath="..\..\lib\CSiAPIv1.dll">` voi `Private=False`
(khong copy ra thu muc output).
