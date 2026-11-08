"""Xay file Excel tu ocr_results.json (da sua tay cac o bi flag).

Moi bang (band) -> 1 sheet, dung layout detector cua ETABS Load
Assigner hieu (giong file mau LONG PHU BC-5):
  dong 1: tieu de | ten diem (moi diem 3 cot)
  dong 2: 'Foundation loads (action loads)' | Hx | Hy | Vz ...
  dong 3: 'Tolerance +/- 20%' | [kN] ...
  dong 4+: ten tai | +/- | gia tri (so; khoang '-3/+6' de dang text)
Kem sheet README (nguon, cach nhap) va sheet KIEM TRA (cac o OCR
khong chac — doi chieu lai voi ban ve PDF goc).
"""
from __future__ import annotations

import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Font

WORK = Path(__file__).resolve().parent
OUT_XLSX = Path("/home/hatch/workspace/your_files/BANG_NOI_LUC_BC-5A_B.xlsx")
OCR_JSON = WORK / "ocr_results.json"
PDF_SRC = "/home/hatch/workspace/user/files/BANG_NOI_LUC_0_qo1t.pdf"

TITLES = {
    "SH4-T1": "LONG PHU BC-5 A/B",
    "SH4-T2": "LONG PHU BC-5 A/B",
    "SH4-T3": "LONG PHU BC-5 A/B",
    "SH4-T4": "LONG PHU BC-5 A/B",
    "SH5-T1": "LONG PHU BC-5 A/B",
    "SH5-T2": "LONG PHU BC-5 A/B",
    "SH5-T3": "LONG PHU BC-5 A/B",
    "SH5-T4": "LONG PHU BC-5 A/B",
    "SH6-T1": "LONG PHU BC-5 A/B",
    "SH6-T2": "LONG PHU BC-5 A/B",
    "SH6-T3a": "LONG PHU BC-5 A/B",
    "SH6-EHOUSE": "LONG PHU BC-5A/B E-HOUSE",
    "SH6-TU": "LONG PHU BC-5",
    "SH6-S781": "LONG PHU BC-5 A/B",
    "SH6-S801": "LONG PHU BC-5 A/B",
    "SH6-S821": "LONG PHU BC-5 A/B",
    "SH6-S841": "LONG PHU BC-5 A/B",
}

SHEET_ORDER = ["SH4-T1", "SH4-T2", "SH4-T3", "SH4-T4",
               "SH5-T1", "SH5-T2", "SH5-T3", "SH5-T4",
               "SH6-T1", "SH6-T2", "SH6-T3a", "SH6-EHOUSE", "SH6-TU",
               "SH6-S781", "SH6-S801", "SH6-S821", "SH6-S841"]


def write_table(ws, table):
    title = TITLES.get(table["band"], "LONG PHU BC-5 A/B")
    points = table["points"]
    ws.cell(1, 1, title)
    ws.cell(2, 1, "Foundation loads (action loads)")
    ws.cell(3, 1, "Tolerance +/- 20%")
    for k, pt in enumerate(points):
        c = 3 + k * 3
        ws.cell(1, c, pt)
        ws.cell(2, c, "Hx")
        ws.cell(2, c + 1, "Hy")
        ws.cell(2, c + 2, "Vz")
        ws.cell(3, c, "[kN]")
        ws.cell(3, c + 1, "[kN]")
        ws.cell(3, c + 2, "[kN]")
    r = 4
    for row in table["rows"]:
        ws.cell(r, 1, row["name"])
        ws.cell(r, 2, "+/-" if row["reversible"] else "")
        for k, pt in enumerate(points):
            c = 3 + k * 3
            comp = row["values"].get(pt, {})
            for j, cn in enumerate(("Hx", "Hy", "Vz")):
                cell = comp.get(cn, {})
                kind = cell.get("kind")
                val = cell.get("value")
                if kind == "int":
                    # o goc viet '+/- 1': giu dung text goc de nguoi doc
                    # thay; detector parse ra 1 (xem parse_cell)
                    raw = cell.get("raw") or ""
                    if str(raw).strip().startswith(("+/-", "-/+", "±")):
                        ws.cell(r, c + j, str(raw).strip())
                    else:
                        ws.cell(r, c + j, val)
                elif kind == "range":
                    ws.cell(r, c + j, f"{val[0]}/{val[1]:+d}")
                elif kind in ("blank", "bad"):
                    ws.cell(r, c + j, "")
                else:
                    ws.cell(r, c + j, "")
        r += 1
    ws.cell(r + 1, 1, "Note: Alle applied loads directly on concrete by client are not included in this table; LFP = Lateral Force Procedure")
    ws.column_dimensions["A"].width = 48
    ws.column_dimensions["B"].width = 6
    for col in range(3, 3 + len(points) * 3):
        ws.column_dimensions[openpyxl.utils.get_column_letter(col)].width = 11
    ws.freeze_panes = "C4"


def main():
    results = json.loads(OCR_JSON.read_text(encoding="utf-8"))
    wb = openpyxl.Workbook()
    readme = wb.active
    readme.title = "README"
    lines = [
        "BANG NOI LUC — LONG PHU BC-5 A/B (chuyen tu file PDF ban ve)",
        f"Nguon: {PDF_SRC}",
        "Ban ve: FOUNDATION & LOADS SH.4 (LP1-TKIS-10EAC-C-M2-DGA-0229), SH.5 (0229), SH.6 (0234) — LONG PHU-1 THERMAL POWER PLANT",
        "Phuong phap: OCR (RapidOCR) tren anh render 200 dpi + phat hien luoi o bang OpenCV. Moi o so da qua kiem tra parse; cac o khong chac nam o sheet KIEM TRA.",
        "Cach nhap vao ETABS Load Assigner: mo app -> Chon file Excel nay -> chon Sheet (ten sheet = ten bang goc, vd SH4-T1) -> Nhan dien bang -> lam theo HUONG_DAN_TEST.md.",
        "Don vi: kN. Cot '+/-' = tai co the dao chieu. O '-3/+6' = khoang min/max.",
        "",
        "Danh sach bang:",
    ]
    for name in SHEET_ORDER:
        t = results.get(name)
        if not t:
            lines.append(f"  - {name}: CHUA OCR")
            continue
        lines.append(f"  - {name}: {len(t['points'])} diem ({', '.join(t['points'])}), {len(t['rows'])} dong tai, {len(t['flags'])} flag")
    for i, ln in enumerate(lines, start=1):
        readme.cell(i, 1, ln)
        if i == 1:
            readme.cell(i, 1).font = Font(bold=True, size=13)
    readme.column_dimensions["A"].width = 130

    for name in SHEET_ORDER:
        t = results.get(name)
        if not t:
            continue
        ws = wb.create_sheet(name)
        write_table(ws, t)

    # sheet KIEM TRA: tat ca flag
    ws = wb.create_sheet("KIEM TRA")
    ws.cell(1, 1, "Cac o OCR khong chac — doi chieu lai voi ban ve PDF goc truoc khi gan hang loat").font = Font(bold=True)
    for j, h in enumerate(["Bang", "O (dong / diem / thanh phan)", "Van de", "OCR doc duoc", "Conf"], start=1):
        ws.cell(2, j, h).font = Font(bold=True)
    r = 3
    for name in SHEET_ORDER:
        t = results.get(name)
        if not t:
            continue
        for f in t["flags"]:
            ws.cell(r, 1, name)
            ws.cell(r, 2, f.get("cell", ""))
            ws.cell(r, 3, f.get("issue", ""))
            ws.cell(r, 4, str(f.get("ocr", "")))
            ws.cell(r, 5, f.get("conf", ""))
            r += 1
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 55
    ws.column_dimensions["C"].width = 60
    ws.column_dimensions["D"].width = 30
    ws.column_dimensions["E"].width = 8
    OUT_XLSX.parent.mkdir(parents=True, exist_ok=True)
    wb.save(OUT_XLSX)
    print(f"wrote {OUT_XLSX}")


if __name__ == "__main__":
    main()
