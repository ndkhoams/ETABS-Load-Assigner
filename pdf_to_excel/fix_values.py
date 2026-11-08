"""Sua tay cac o OCR doc sai trong ocr_results.json — moi gia tri da
doi chieu bang mat voi anh crop o (/tmp/bangnl/watch_cells.png).
Chay sau khi OCR xong (ke ca ban chay bo sung SH6-T3a/SH4-T4/SH5-T3).
"""
import json
from pathlib import Path

JSON = Path(__file__).resolve().parent / "ocr_results.json"


def set_int(t, row, pt, comp, value, raw, note=""):
    for r in t["rows"]:
        if r["name"] == row:
            r["values"][pt][comp] = {"raw": raw, "kind": "int", "value": value}
            t.setdefault("flags", []).append(
                {"cell": f"{row} / {pt} / {comp}",
                 "issue": f"sua tay theo anh crop: {raw!r} -> {value}" + (f" ({note})" if note else "")})
            return
    raise KeyError(row)


def set_range(t, row, pt, comp, lo, hi, raw):
    for r in t["rows"]:
        if r["name"] == row:
            r["values"][pt][comp] = {"raw": raw, "kind": "range", "value": [lo, hi]}
            t.setdefault("flags", []).append(
                {"cell": f"{row} / {pt} / {comp}",
                 "issue": f"sua tay theo anh crop: {raw!r} -> khoang ({lo}, {hi})"})
            return
    raise KeyError(row)


def main():
    data = json.loads(JSON.read_text(encoding="utf-8"))

    # SH4-T1: '6+/2-' la '-3/+9' (anh crop); '-1-12' la '-12'
    t = data["SH4-T1"]
    set_range(t, "Wind +Y", "22 / E", "Vz", -3, 9, "-3/+9")
    set_int(t, "Wind -Y", "21 / E", "Hy", -12, "-12")
    # SH4-T4: '-3/+93/+9' la '-3/+9'
    t = data["SH4-T4"]
    set_range(t, "Wind -Y", "43 / D", "Vz", -3, 9, "-3/+9")
    # SH5-T3: '8-' la '-8'
    t = data["SH5-T3"]
    set_int(t, "Wind -Y", "70 / E", "Hy", -8, "-8")
    # SH5-T4: '6-' la '-9' (anh crop: -9)
    t = data["SH5-T4"]
    set_int(t, "Wind -Y", "79 / E", "Hy", -9, "-9")
    # SH6-T1: o trong la 0
    t = data["SH6-T1"]
    set_int(t, "Special load overload belt BC-5A", "82 / E", "Vz", 0, "0")
    # SH6-T2: '69-' la -69; '67 / -71-71' la khoang 67/-71;
    # '-71 /+67/+67' la khoang -71/+67; diem '88 / D.28' la '88 / D.2'
    t = data["SH6-T2"]
    set_int(t, "Friction +X", "89.1 / D.2", "Hx", -69, "-69")
    set_int(t, "Friction +X", "89.1 / E.2", "Hx", -69, "-69")
    set_range(t, "Wind +Y", "85.1 / E.2", "Vz", 67, -71, "67 / -71")
    set_range(t, "Wind -Y", "85.1 / E.2", "Vz", -71, 67, "-71 / +67")
    set_int(t, "Live load Lifting jack #1 (service load 16 kN)", "87 / E.2", "Hx", 0, "0")
    if "88 / D.28" in t["points"]:
        t["points"] = ["88 / D.2" if p == "88 / D.28" else p for p in t["points"]]
        for r in t["rows"]:
            if "88 / D.28" in r["values"]:
                r["values"]["88 / D.2"] = r["values"].pop("88 / D.28")
        t.setdefault("flags", []).append(
            {"cell": "header 88 / D.28", "issue": "ten diem OCR '88 / D.28' -> sua tay '88 / D.2' theo thu tu diem + anh strip"})
    # SH6-T3a: '0/' va '>' la 0 (vong tron revision de len o)
    t = data["SH6-T3a"]
    for row in ("Live load Lifting jack #1 (service load 16 kN)",
                "Live load Lifting jack #2 (service load 16 kN)"):
        set_int(t, row, "92 / E.1", "Vz", 0, "0")
    set_int(t, "Temperatur DT = 16°C", "92 / E.1", "Vz", 0, "0")
    # SH6-TU: chuan hoa khoang trang ten dong (giu nguyen y nghia MA)
    t = data["SH6-TU"]
    rename = {
        "EarthquakeX(q=1,5;0,12g;MA)": "Earthquake X (q = 1,5; 0,12g; MA)",
        "EarthquakeY(q=1,5;0,12g:MA)": "Earthquake Y (q = 1,5; 0,12g; MA)",
        "EarthquakeZ(q=1,5;0,094g;MA)": "Earthquake Z (q = 1,5; 0,094g; MA)",
        "SpecialloadbeltbreakBC-5A": "Special load belt break BC-5A",
        "SpecialloadbeltbreakBC-5B": "Special load belt break BC-5B",
    }
    for r in t["rows"]:
        if r["name"] in rename:
            r["name"] = rename[r["name"]]
    JSON.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("fix_values OK")


if __name__ == "__main__":
    main()
