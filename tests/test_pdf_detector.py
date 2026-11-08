"""Test PDF: tao PDF bang that (reportlab Table) roi chay detect_pdf.

Day van la fixture tong hop — bang trong PDF duoc ve lai tu cac so
trong anh, khong phai file PDF that cua client.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etabs_loader.detector import detect_pdf


def _make_pdf(path):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
    data = [
        ["LONG PHU BC-5 A/B", "", "", "20 / D", "", "", "20 / E", "", ""],
        ["Foundation loads (action loads)", "", "", "Hx", "Hy", "Vz", "Hx", "Hy", "Vz"],
        ["Tolerance +/- 20%", "", "", "[kN]", "[kN]", "[kN]", "[kN]", "[kN]", "[kN]"],
        ["Dead loads", "", "", 0, -2, 19, 0, 2, 19],
        ["Live load roof (inacc.)", "", "", 0, -1, 21, 0, 1, 21],
        ["Wind +Y", "", "", 0, 7, -11, 0, 6, "-3/+6"],
        ["Imperfektion X", "+/-", "", -1, 0, 0, -1, 0, 0],
    ]
    t = Table(data, colWidths=[170, 30, 10, 35, 35, 35, 35, 35, 35])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]))
    SimpleDocTemplate(str(path), pagesize=A4).build([t])


def test_detect_pdf_table(tmp_path):
    pdf = tmp_path / "loads.pdf"
    _make_pdf(pdf)
    t = detect_pdf(str(pdf))
    assert t.points == ["20 / D", "20 / E"], t.points
    assert len(t.rows) == 4, [r.name for r in t.rows]
    dead = [r for r in t.rows if r.name == "Dead loads"][0]
    assert dead.values["20 / D"]["Vz"].value == 19
    wy = [r for r in t.rows if r.name == "Wind +Y"][0]
    assert wy.values["20 / E"]["Vz"].kind == "range"
    assert [r for r in t.rows if r.name == "Imperfektion X"][0].reversible is True
