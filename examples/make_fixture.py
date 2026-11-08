"""Tao fixture TONG HOP theo anh user gui (image-18.png).

CANH BAO — day KHONG phai file that cua client: cac so duoc chep tay
tu anh screenshot, chi de test detector/assigner offline. Theo skill
real_file_fixtures, test tren fixture nay la bang chung yeu; ket qua
quyet dinh phai chay lai tren file Excel/PDF that (LP1-PB19-10EAC-...).
"""
from __future__ import annotations

import openpyxl

POINTS = ["20 / D", "20 / E", "27 / D", "27 / E"]

# (ten dong, +/-?, {diem: (Hx, Hy, Vz)}) — so chep tu anh, diem 20/D & 20/E day du,
# diem 27 chi co dong Dead loads doc duoc trong anh, cac dong khac de 0.
ROWS = [
    ("Dead loads", "", {"20 / D": (0, -2, 19), "20 / E": (0, 2, 19), "27 / D": (0, -2, 23), "27 / E": (0, 2, 23)}),
    ("Live load belt conveyor load BC-5A", "", {}),
    ("Live load belt conveyor load BC-5B", "", {}),
    ("Live load incrustation", "", {}),
    ("Live load walkway left side (5,0kN/m²)", "", {}),
    ("Live load walkway middle (5,0kN/m²)", "", {}),
    ("Live load walkway right side (5,0kN/m²)", "", {}),
    ("Live load platforms and stairs", "", {}),
    ("Live load roof (inacc.)", "", {"20 / D": (0, -1, 21), "20 / E": (0, 1, 21)}),
    ("Live load belt tension BC-5A max/min", "", {}),
    ("Live load belt tension BC-5B max/min", "", {}),
    ("Imperfektion X", "+/-", {"20 / D": (-1, 0, 0), "20 / E": (-1, 0, 0)}),
    ("Imperfektion Y", "+/-", {"20 / D": (0, 0, -1), "20 / E": (0, 0, 1)}),
    ("Friction +X", "+/-", {}),
    ("Wind +X", "", {"20 / D": (1, 0, -1), "20 / E": (1, -1, -1)}),
    ("Wind -X", "", {"20 / D": (-1, 0, 1), "20 / E": (-1, 1, 1)}),
    ("Wind +Y", "", {"20 / D": (0, 7, -11), "20 / E": (0, 6, "-3/+6")}),
    ("Wind -Y", "", {"20 / D": (0, -6, "-3/+6"), "20 / E": (0, -7, -11)}),
    ("Temperatur DT = 16°C", "+/-", {"20 / D": (0, -1, 0), "20 / E": (0, -1, 0)}),
    ("Earthquake X (LFP; 0,12g)", "+/-", {"20 / D": (1, -1, 1), "20 / E": (1, -1, -1)}),
    ("Earthquake Y (LFP; 0,12g)", "+/-", {"20 / D": (0, 3, -3), "20 / E": (0, 3, 3)}),
    ("Earthquake Z (LFP; 0,94g)", "+/-", {"20 / D": (0, -1, 2), "20 / E": (0, 1, 2)}),
    ("Special load overload belt BC-5A", "", {}),
    ("Special load overload belt BC-5B", "", {}),
    ("Live load Lifting jack #1 (service load 16 kN)", "", {}),
    ("Live load Lifting jack #2 (service load 16 kN)", "", {}),
]

PATTERNS = [
    ("BC1", "No", "Live", 0), ("BC2", "No", "Live", 0),
    ("BT1", "No", "Live", 0), ("BT2", "No", "Live", 0),
    ("DLS", "No", "Super Dead", 0), ("EX", "No", "Seismic", 0),
    ("EY", "No", "Seismic", 0), ("EZ", "No", "Seismic", 0),
    ("F", "No", "Live", 0), ("LL1", "No", "Live", 0),
    ("LL2", "No", "Live", 0), ("LL3", "No", "Live", 0),
    ("LL4", "No", "Live", 0), ("LL5", "No", "Live", 0),
    ("LLR", "No", "Roof Live", 0), ("NX", "No", "Notional", 0),
    ("NY", "No", "Notional", 0), ("SLL1", "No", "Other", 0),
    ("SLL2", "No", "Other", 0), ("SPL1", "No", "Other", 0),
    ("SPL2", "No", "Other", 0), ("SW", "No", "Dead", 1),
    ("T", "No", "Temperature", 0), ("WX-", "No", "Wind", 0),
    ("WX+", "No", "Wind", 0), ("WY-1", "No", "Wind", 0),
    ("WY-2", "No", "Wind", 0), ("WY+1", "No", "Wind", 0),
    ("WY+2", "No", "Wind", 0),
]


def build(path: str):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Foundation loads"
    ws.cell(1, 1, "LONG PHU BC-5 A/B")
    ws.cell(2, 1, "Foundation loads (action loads)")
    ws.cell(3, 1, "Tolerance +/- 20%")
    # dong ten diem (row 1... dung layout 3 dong header giong anh)
    # Dat lai theo layout detector hieu: point row, Hx row, unit row
    # -> dung row 1-3 cho bang dau tien
    for k, p in enumerate(POINTS):
        c = 3 + k * 3  # cot C bat dau (A=ten, B=+/-, C..)
        ws.cell(1, c, p)
        ws.cell(2, c, "Hx")
        ws.cell(2, c + 1, "Hy")
        ws.cell(2, c + 2, "Vz")
        ws.cell(3, c, "[kN]")
        ws.cell(3, c + 1, "[kN]")
        ws.cell(3, c + 2, "[kN]")
    r = 4
    for name, sign, vals in ROWS:
        ws.cell(r, 1, name)
        ws.cell(r, 2, sign)
        for k, p in enumerate(POINTS):
            c = 3 + k * 3
            hx, hy, vz = vals.get(p, (0, 0, 0))
            ws.cell(r, c, hx)
            ws.cell(r, c + 1, hy)
            ws.cell(r, c + 2, vz)
        r += 1
    ws.cell(r + 1, 1, "Note: Alle applied loads directly on concrete by client are not included in this table.")
    # sheet pattern
    ws2 = wb.create_sheet("Load Patterns")
    ws2.cell(1, 1, "TABLE: Load Pattern Definitions")
    for j, h in enumerate(["Name", "Is Auto Load", "Type", "Self Weight Multiplier", "GUID"], start=1):
        ws2.cell(2, j, h)
    for i, (nm, auto, typ, sw) in enumerate(PATTERNS, start=3):
        ws2.cell(i, 1, nm)
        ws2.cell(i, 2, auto)
        ws2.cell(i, 3, typ)
        ws2.cell(i, 4, sw)
        ws2.cell(i, 5, f"00000000-0000-4000-8000-{i:012d}")
    wb.save(path)


if __name__ == "__main__":
    import sys
    build(sys.argv[1] if len(sys.argv) > 1 else "longphu_bc5_synthetic.xlsx")
    print("wrote fixture")
