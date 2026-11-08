"""Sua tay bang SH6-EHOUSE trong ocr_results.json theo anh strip
(tu doc bang mat — ten diem nhieu dong, OCR khong ghep duoc).

Doc tu /tmp/bangnl/strips/SH6-EHOUSE.png:
- 6 diem, moi diem la nhom ho tro (vd '20 to 32 / B.3 / B.5; ...').
- 9 dong tai; Imperfektion X co dau '+/-' nam trong tung o
  (gia tri 0, dao chieu True).
"""
import json
from pathlib import Path

JSON = Path(__file__).resolve().parent / "ocr_results.json"

POINTS = [
    "20 to 32 / B.3 / B.5; 35 to 48 / B.3 / B.5; 51 to 57 / B.3 / B.5; 70 / B.3 / B.5; 73 to 84 / B.3 / B.5; 84.2 / B.3 / B.5",
    "20 to 32 / B.4 / B.6; 35 to 48 / B.4 / B.6; 51 to 57 / B.4 / B.6; 70 / B.4 / B.6; 73 to 84 / B.4 / B.6; 84.2 / B.4 / B.6",
    "33 / B.3 / B.5; 49 / B.3 / B.5; 71 / B.3 / B.5",
    "33 / B.4 / B.6; 49 / B.4 / B.6; 71 / B.4 / B.6",
    "34 / B.3 / B.5; 50 / B.3 / B.5; 72 / B.3 / B.5",
    "34 / B.4 / B.6; 50 / B.4 / B.6; 72 / B.4 / B.6",
]

# (ten dong, dao chieu, [(Hx, Hy, Vz) x 6 diem])
ROWS = [
    ("Dead loads", False, [(0, 0, 3)] * 6),
    ("Live load belt conveyor load BC5-A/B", False, [(0, 0, 2)] * 6),
    ("Live load incrustation", False, [(0, 0, 0)] * 6),
    ("Imperfektion X", True, [(0, 0, 0)] * 6),
    ("Temperatur DT = 16°C", True, [(0, 0, 0)] * 6),
    ("Earthquake X (q = 1,5; 0,12g; LFP)", True,
     [(0, 0, 0), (0, 0, 0), (10, 0, -3), (10, 0, -3), (0, 0, 3), (0, 0, 3)]),
    ("Earthquake Y (q = 1,5; 0,12g; LFP)", True,
     [(0, 1, -1), (0, 1, 1), (0, 1, -1), (0, 1, 1), (0, 1, -1), (0, 1, 1)]),
    ("Earthquake Z (q = 1,5; 0,094g; LFP)", True, [(0, 0, 1)] * 6),
    ("Special load overload belt BC-5A/B", False, [(0, 0, 4)] * 6),
]


def _cell(v):
    return {"raw": str(v), "kind": "int", "value": v}


def main():
    data = json.loads(JSON.read_text(encoding="utf-8"))
    t = data["SH6-EHOUSE"]
    t["points"] = POINTS
    rows = []
    for name, rev, vals in ROWS:
        values = {}
        for pt, (hx, hy, vz) in zip(POINTS, vals):
            values[pt] = {"Hx": _cell(hx), "Hy": _cell(hy), "Vz": _cell(vz)}
        rows.append({"name": name, "reversible": rev, "values": values})
    t["rows"] = rows
    t["flags"] = [{"cell": "toan bang",
                   "issue": "ten diem + dong tai da sua tay theo anh strip (OCR ghep sai ten diem nhieu dong); gia tri OCR giu nguyen, da doi chieu bang mat"}]
    JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("SH6-EHOUSE fixed:", len(POINTS), "diem,", len(rows), "dong")


if __name__ == "__main__":
    main()
