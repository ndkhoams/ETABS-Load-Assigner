"""Test tren file Excel THAT chuyen tu ban ve PDF LONG PHU BC-5
(BANG_NOI_LUC_0_qo1t.pdf — 3 to A0, SH.4/5/6).

Khac voi test_assigner.py (fixture tong hop chep tay tu anh):
file nay la ket qua OCR + doi chieu bang mat tung o kha nghi,
nen day la 'fixture vang' cho detector/assigner.
"""
import os

import pytest

from etabs_loader.detector import detect_file
from etabs_loader.assigner import build_assignments
from etabs_loader.mapping import Profile

XLSX = os.path.join(os.path.dirname(__file__), "..", "examples", "BANG_NOI_LUC_BC-5A_B.xlsx")

EXPECTED = {
    "SH4-T1": (13, 26), "SH4-T2": (12, 26), "SH4-T3": (13, 26), "SH4-T4": (10, 26),
    "SH5-T1": (13, 26), "SH5-T2": (13, 26), "SH5-T3": (13, 26), "SH5-T4": (10, 26),
    "SH6-T1": (13, 26), "SH6-T2": (13, 26), "SH6-T3a": (6, 26),
    "SH6-EHOUSE": (6, 9), "SH6-TU": (6, 10),
    "SH6-S781": (12, 4), "SH6-S801": (12, 4), "SH6-S821": (12, 4), "SH6-S841": (6, 4),
}


@pytest.mark.parametrize("sheet,counts", list(EXPECTED.items()))
def test_real_excel_sheet_counts(sheet, counts):
    t = detect_file(XLSX, sheet=sheet)
    assert (len(t.points), len(t.rows)) == counts, (sheet, t.warnings)
    assert not t.warnings


def test_real_excel_spot_values():
    t = detect_file(XLSX, sheet="SH4-T1")
    dl = next(r for r in t.rows if r.name == "Dead loads")
    assert (dl.values["20 / D"]["Hx"].value,
            dl.values["20 / D"]["Hy"].value,
            dl.values["20 / D"]["Vz"].value) == (0, -2, 19)
    wy = next(r for r in t.rows if r.name == "Wind +Y")
    v = wy.values["22 / E"]["Vz"]
    assert v.kind == "range" and (v.vmin, v.vmax) == (-3, 9)
    # o '+/- 1' bang 90/D.1 -> so 1
    t3 = detect_file(XLSX, sheet="SH6-T3a")
    wy3 = next(r for r in t3.rows if r.name == "Wind +Y")
    assert wy3.values["90 / D.1"]["Hx"].value == 1
    # khoang '67/-71' bang 85.1
    t2 = detect_file(XLSX, sheet="SH6-T2")
    wy2 = next(r for r in t2.rows if r.name == "Wind +Y")
    v2 = wy2.values["85.1 / E.2"]["Vz"]
    assert v2.kind == "range" and (v2.vmin, v2.vmax) == (67, -71)


def test_real_excel_assigner_20d():
    import json
    prof = Profile.from_dict(json.load(open(os.path.join(
        os.path.dirname(__file__), "..", "examples", "profile_longphu_example.json"))))
    t = detect_file(XLSX, sheet="SH4-T1")
    res = build_assignments(t, "20 / D", prof)
    got = {a.pattern: (a.fx, a.fy, a.fz) for a in res.assignments}
    assert got["DLS"] == (0, -2, -19)
    assert got["WY+1"] == (0, 7, 11)
    assert got["WY-1"] == (0, -6, -6)  # khoang -3/+6 -> max_abs +6 -> Fz -6
