"""Tests ETABS Load Assigner v0.1 — chay tren fixture TONG HOP.

Luu y (real_file_fixtures): pass tren fixture tong hop chi chung minh
logic chay dung voi dang bang trong anh; KHONG thay the test tren
file Excel/PDF that cua client.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from etabs_loader.assigner import build_assignments
from etabs_loader.detector import detect_excel, detect_file, parse_cell
from etabs_loader.etabs_api import MockEtabs
from etabs_loader.mapping import AxisMapping, Profile, suggest_pattern

FIXTURE = Path(__file__).resolve().parents[1] / "examples" / "longphu_bc5_synthetic.xlsx"


def _profile():
    p = Profile()
    p.pattern_map = {
        "Dead loads": "DLS",
        "Live load roof (inacc.)": "LLR",
        "Imperfektion X": "NX",
        "Imperfektion Y": "NY",
        "Wind +X": "WX+",
        "Wind -X": "WX-",
        "Wind +Y": "WY+1",
        "Wind -Y": "WY-1",
        "Earthquake X (LFP; 0,12g)": "EX",
        "Earthquake Y (LFP; 0,12g)": "EY",
        "Earthquake Z (LFP; 0,94g)": "EZ",
    }
    return p


def test_parse_cell_range():
    lv = parse_cell("-3/+6")
    assert lv.kind == "range" and lv.vmin == -3 and lv.vmax == 6
    assert parse_cell(19).value == 19
    assert parse_cell("").kind == "blank"
    assert parse_cell(None).kind == "blank"


def test_detector_finds_points_rows_patterns():
    t = detect_excel(str(FIXTURE))
    assert t.points == ["20 / D", "20 / E", "27 / D", "27 / E"], t.points
    assert len(t.rows) == 26, len(t.rows)
    assert len(t.patterns) == 29, len(t.patterns)
    assert [p.name for p in t.patterns[:3]] == ["BC1", "BC2", "BT1"]
    dead = [r for r in t.rows if r.name == "Dead loads"][0]
    assert dead.values["20 / D"]["Hy"].value == -2
    assert dead.values["20 / D"]["Vz"].value == 19
    assert dead.values["20 / E"]["Hy"].value == 2
    wind_y = [r for r in t.rows if r.name == "Wind +Y"][0]
    assert wind_y.values["20 / E"]["Vz"].kind == "range"
    assert wind_y.values["20 / E"]["Vz"].vmax == 6
    imperf = [r for r in t.rows if r.name == "Imperfektion X"][0]
    assert imperf.reversible is True


def test_axis_default_vz_down_to_minus_z():
    ax = AxisMapping()  # mac dinh Vz -> -Z
    assert ax.apply(0, -2, 19) == (0, -2, -19)
    assert ax.apply(1, 0, -1) == (1, 0, 1)


def test_assigner_20D_dead_and_wind():
    t = detect_excel(str(FIXTURE))
    res = build_assignments(t, "20 / D", _profile())
    by_pat = {a.pattern: a for a in res.assignments}
    # Dead: Hy=-2 -> Fy=-2, Vz=19 -> Fz=-19
    assert by_pat["DLS"].fy == -2 and by_pat["DLS"].fz == -19
    # Wind +Y: Hy=7, Vz=-11 -> Fy=7, Fz=+11
    assert by_pat["WY+1"].fy == 7 and by_pat["WY+1"].fz == 11
    # Wind -Y o 20/D co khoang -3/+6 -> max_abs = +6 -> Fz=-6
    assert by_pat["WY-1"].fz == -6, by_pat["WY-1"]
    # hang 0 bi bo qua, hang chua match bi skip (khong crash)
    assert any("chua match pattern" in k for k, _ in res.skipped)


def test_assigner_reversible_both_creates_neg():
    t = detect_excel(str(FIXTURE))
    p = _profile()
    p.reversible_mode = "both"
    res = build_assignments(t, "20 / D", p)
    negs = [a for a in res.assignments if a.negated]
    assert any(a.pattern == "NX_NEG" and a.fx == 1 for a in negs), negs


def test_suggest_pattern():
    avail = MockEtabs().pattern_names()
    assert suggest_pattern("Dead loads", avail) == "DLS"
    assert suggest_pattern("Wind +X", avail) == "WX+"
    assert suggest_pattern("Earthquake Y (LFP; 0,12g)", avail) == "EY"
    assert suggest_pattern("Imperfektion X", avail) == "NX"


def test_mock_assign_roundtrip():
    t = detect_excel(str(FIXTURE))
    mock = MockEtabs()
    res = build_assignments(t, "20 / D", _profile())
    for a in res.assignments:
        mock.assign_force(a.etabs_joint, a.pattern, a.values())
    v = mock.get_assignment("20 / D", "DLS")
    assert v == [0, -2, -19, 0, 0, 0], v
    # ghi de: gan lai chi giu 1 ban
    mock.assign_force("20 / D", "DLS", [0, -2, -19, 0, 0, 0], replace=True)
    assert len([a for a in mock.assignments if a[1] == "DLS"]) == 1


def test_profile_save_load_roundtrip(tmp_path):
    p = _profile()
    p.point_alias = {"20 / D": "J-20D"}
    p.axis.vz_sign = -1
    f = tmp_path / "prof.json"
    p.save(str(f))
    p2 = Profile.load(str(f))
    assert p2.pattern_map["Dead loads"] == "DLS"
    assert p2.point_alias["20 / D"] == "J-20D"
    assert p2.axis.vz_sign == -1
