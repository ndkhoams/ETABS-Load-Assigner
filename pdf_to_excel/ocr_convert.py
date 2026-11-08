"""OCR chuyen bang tai mong PDF (ban ve A0, bang la anh raster, khong co
text layer) thanh du lieu co cau truc -> file Excel dung format
ETABS Load Assigner.

Quy trinh moi bang (band):
  1. Cat strip tu anh render 200 dpi theo toa do pt (lay tu bbox cac
     tile anh nhiung trong PDF — xem BANDS).
  2. Phat hien luoi ke (duong ngang/doc) bang OpenCV morphology.
  3. OCR toan strip 1 lan bang RapidOCR, gan moi doan text vao o
     theo toa do tam.
  4. Parse o so / khoang '-3/+6' / cot '+/-', danh dau (flag) cac o
     khong chac de nguoi kiem tra lai bang mat.

Ket qua trung gian luu JSON de sua tay ma khong phai OCR lai.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

PDF_PATH = "/home/hatch/workspace/user/files/BANG_NOI_LUC_0_qo1t.pdf"
RENDER_DIR = Path("/tmp/bangnl")
WORK = Path(__file__).resolve().parent
OUT_JSON = WORK / "ocr_results.json"
DPI = 200
SCALE = DPI / 72.0

# (page, ten, x0, top, x1, bottom) — toa do pt, lay tu bbox tile anh
# trong PDF (pdfplumber page.images). Padding +- vai pt khi cat.
BANDS = [
    (1, "SH4-T1", 74, 303, 2572, 774),
    (1, "SH4-T2", 74, 819, 2568, 1320),
    (1, "SH4-T3", 78, 1380, 2573, 1848),
    (1, "SH4-T4", 74, 1882, 2021, 2341),
    (2, "SH5-T1", 36, 348, 2686, 854),
    (2, "SH5-T2", 36, 860, 2421, 1316),
    (2, "SH5-T3", 36, 1322, 2421, 1777),
    (2, "SH5-T4", 36, 1794, 2025, 2265),
    (3, "SH6-T1", 49, 305, 2589, 786),
    (3, "SH6-T2", 49, 801, 2589, 1284),
    (3, "SH6-T3a", 49, 1297, 1438, 1794),
    (3, "SH6-EHOUSE", 1455, 1297, 2624, 1579),
    (3, "SH6-TU", 1450, 1630, 2733, 1846),
    (3, "SH6-S781", 49, 1877, 1941, 1979),
    (3, "SH6-S801", 49, 1998, 1941, 2101),
    (3, "SH6-S821", 49, 2118, 1941, 2220),
    (3, "SH6-S841", 49, 2235, 1117, 2337),
]

KNOWN_ROWS = [
    "Dead loads",
    "Live load belt conveyor load BC-5A",
    "Live load belt conveyor load BC-5B",
    "Live load incrustation",
    "Live load walkway left side (5,0kN/m²)",
    "Live load walkway middle (5,0kN/m²)",
    "Live load walkway right side (5,0kN/m²)",
    "Live load platforms and stairs",
    "Live load roof (inacc.)",
    "Live load belt tension BC-5A max/min",
    "Live load belt tension BC-5B max/min",
    "Imperfektion X",
    "Imperfektion Y",
    "Friction +X",
    "Wind +X",
    "Wind -X",
    "Wind +Y",
    "Wind -Y",
    "Temperatur DT = 16°C",
    "Earthquake X (LFP; 0,12g)",
    "Earthquake Y (LFP; 0,12g)",
    "Earthquake Z (LFP; 0,94g)",
    "Special load overload belt BC-5A",
    "Special load overload belt BC-5B",
    "Live load Lifting jack #1 (service load 16 kN)",
    "Live load Lifting jack #2 (service load 16 kN)",
]

NUM_RE = re.compile(r"^[+-]?\d+$")
RANGE_RE = re.compile(r"^([+-]?\d+)\s*/\s*([+-])\s*(\d+)$")


def crop_strip(page: int, band):
    _, name, x0, top, x1, bottom = band
    im = Image.open(RENDER_DIR / f"pg200-{page}.png")
    box = (int((x0 - 4) * SCALE), int((top - 3) * SCALE),
           int((x1 + 4) * SCALE), int((bottom + 4) * SCALE))
    strip = im.crop(box)
    out = RENDER_DIR / "strips" / f"{name}.png"
    out.parent.mkdir(exist_ok=True)
    strip.save(out)
    return out, strip


def _line_centers(mask: np.ndarray, axis: int) -> list:
    """Tra ve tam cac duong ke: mask la anh nhi phan duong ke.
    axis=0 -> duong ngang (quet theo hang), axis=1 -> duong doc."""
    proj = mask.sum(axis=axis)  # so pixel den tren moi hang/cot
    thr = mask.shape[1 - axis] * 0.25  # duong ke dai it nhat 25% chieu dai
    on = proj > thr
    centers = []
    i = 0
    while i < len(on):
        if on[i]:
            j = i
            while j < len(on) and on[j]:
                j += 1
            centers.append((i + j - 1) / 2.0)
            i = j
        else:
            i += 1
    return centers


def detect_grid(strip_path: Path):
    img = cv2.imread(str(strip_path), cv2.IMREAD_GRAYSCALE)
    _, bw = cv2.threshold(img, 180, 255, cv2.THRESH_BINARY_INV)
    h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (60, 1))
    v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 60))
    h_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, h_kernel)
    v_lines = cv2.morphologyEx(bw, cv2.MORPH_OPEN, v_kernel)
    rows = _line_centers(h_lines, axis=1)
    cols = _line_centers(v_lines, axis=0)
    return rows, cols, img.shape


def ocr_strip(strip_path: Path):
    """OCR strip theo 3 khoanh doc chong lap — anh strip qua rong nen OCR
    mot lan bo sot nhieu so (771 doan) trong khi chia khoanh bat duoc
    gan nhu day du (1234 doan, ca ten diem o dong header)."""
    from rapidocr_onnxruntime import RapidOCR
    from PIL import Image
    eng = RapidOCR()
    im = Image.open(strip_path)
    W, H = im.size
    items = []
    chunks = [(0, 2500), (2200, 4700), (4400, W)] if W > 5000 else [(0, W)]
    for k, (x0, x1) in enumerate(chunks):
        crop = im.crop((x0, 0, x1, H))
        tmp = RENDER_DIR / "strips" / f"_chunk{k}.png"
        crop.save(tmp)
        result, _ = eng(str(tmp))
        for box, txt, conf in (result or []):
            cx = sum(p[0] for p in box) / len(box) + x0
            cy = sum(p[1] for p in box) / len(box)
            items.append({"cx": cx, "cy": cy, "text": txt, "conf": float(conf)})
    # khu trung lap: trung lap cac doan gan nhu trung nhau (cung text, tam cach < 14px)
    items.sort(key=lambda z: -z["conf"])
    kept = []
    for it in items:
        dup = False
        for k in kept:
            if (abs(it["cx"] - k["cx"]) < 14 and abs(it["cy"] - k["cy"]) < 14
                    and it["text"].strip() == k["text"].strip()):
                dup = True
                break
        if not dup:
            kept.append(it)
    return kept


def assign_cells(items, rows, cols):
    """Gan text OCR vao luoi o. Tra ve dict (r,c) -> (text, min_conf)."""
    cells = {}
    for it in items:
        r = _find_idx(it["cy"], rows)
        c = _find_idx(it["cx"], cols)
        if r is None or c is None:
            continue
        cur = cells.get((r, c))
        if cur is None:
            cells[(r, c)] = (it["text"], it["conf"], it["cx"])
        else:
            # trung lap giua 2 khoanh OCR: cung text thi giu conf cao nhat
            if it["text"].strip() == cur[0].strip():
                if it["conf"] > cur[1]:
                    cells[(r, c)] = (cur[0], it["conf"], cur[2])
                continue
            # ghep 2 manh trong cung o theo thu tu x
            sep = "" if _looks_number(it["text"]) and _looks_number(cur[0]) else " "
            if it["cx"] < cur[2]:
                cells[(r, c)] = (it["text"] + sep + cur[0], min(cur[1], it["conf"]), cur[2])
            else:
                cells[(r, c)] = (cur[0] + sep + it["text"], min(cur[1], it["conf"]), cur[2])
    return {k: (v[0], v[1]) for k, v in cells.items()}


def _find_idx(v, bounds):
    for i in range(len(bounds) - 1):
        if bounds[i] - 3 <= v < bounds[i + 1] + 3:
            return i
    return None


def _looks_number(s):
    return bool(re.search(r"\d", s))


def _dedupe_frags(frags):
    """Bo manh thua do OCR tach/trung lap: manh ma (bo khoang, '/')
    la chuoi con cua manh khac, hoac trung het manh khac.
    Vd ['21', '21 / E'] -> ['21 / E']; ['34 /', '34 / E'] -> ['34 / E'];
    ['48 / D', '48 / D'] -> ['48 / D']; ['23 / E', 'E'] -> ['23 / E']."""
    def norm(s):
        return re.sub(r"[\s/]", "", s)
    out = []
    for f in frags:
        nf = norm(f)
        if not nf:
            continue
        if any(nf != norm(g) and nf in norm(g) for g in frags if g != f):
            continue
        if f not in out:
            out.append(f)
    return out


def _canonical_row(label: str):
    """Tra ve ten chuan trong KNOWN_ROWS neu giong ro, khong thi None.
    Nguong cao (0.85) + cam: cac dong TU/E-HOUSE co '(q = 1,5; ...; MA)'
    hay 'belt break' la loai tai KHAC, khong duoc chuan hoa thanh dong
    LFP/overload cua BC-5 (da tung nhan nham o ban chay dau)."""
    import difflib
    if not label:
        return None
    low = label.lower()
    if "ma)" in low or "belt break" in low or "beltbreak" in low:
        return None
    # dong gop A/B (vd 'Special load overload belt BC-5A/B') la dong
    # khac voi dong BC-5A rieng — khong chuan hoa
    if re.search(r"a/b", low):
        return None
    m = difflib.get_close_matches(label, KNOWN_ROWS, n=1, cutoff=0.85)
    return m[0] if m else None


def clean_num(raw: str):
    """Parse o so: tra ve (gia_tri, loai, ghi_chu).
    loai: 'int' | 'range' | 'blank' | 'bad'
    O co the viet '+/- 0' / '-/+ 0' (dau +/- nam trong o, vd bang
    E-HOUSE) — bo tien to +/- truoc khi parse, gia tri la so sau no."""
    if raw is None:
        return None, "blank", "o trong"
    s = raw.strip()
    s = (s.replace("O", "0").replace("o", "0")
          .replace("−", "-").replace("–", "-").replace("—", "-")
          .replace(" ", "").replace(",", ""))
    s = re.sub(r"^(\+/-|-\/\u002b|±)+", "", s)
    if s in ("", "-", "--"):
        return None, "blank", "o trong"
    if NUM_RE.match(s):
        return int(s), "int", ""
    m = RANGE_RE.match(s)
    if m:
        return (int(m.group(1)), int(m.group(2) + m.group(3))), "range", ""
    # dang '-3/+6' bi tach dau tru: '+6'/'-3' rieng le da ghep sai
    if re.match(r"^[+-]?\d+/[+-]?\d+$", s):
        a, b = s.split("/")
        return (int(a), int(b)), "range", ""
    return None, "bad", f"khong parse duoc: {raw!r} -> {s!r}"


def parse_band(band, rows, cols, cells):
    _, name, _, _, _, _ = band
    flags = []
    n_row = len(rows) - 1
    n_col = len(cols) - 1
    # 3 dong header: 0=ten diem, 1=Hx/Hy/Vz, 2=[kN]; con lai la dong tai
    # cot 0 = ten tai, cot 1 = +/-, cac cot sau: 3 cot/diem
    data_cols = n_col - 2
    if data_cols % 3 != 0:
        flags.append({"cell": "header", "issue": f"so cot du lieu {data_cols} khong chia het cho 3"})
    n_points = data_cols // 3
    points = []
    for k in range(n_points):
        c0 = 2 + k * 3
        frags = []
        conf = 1.0
        for c in (c0, c0 + 1, c0 + 2):
            t, cf = cells.get((0, c), ("", 1.0))
            if t:
                frags.append(t.strip())
                conf = min(conf, cf)
        # ghep cac manh ten diem, roi trich dung mau 'so / chu'
        # (vd '21 / E', '79.1 / S.26', '85.1 / D.2'); lay match pho
        # bien nhat de triet trung lap do OCR tach ('48 / D48 / D').
        frags = _dedupe_frags(frags)
        txt = re.sub(r"\s+", " ", " ".join(frags)).strip()
        txt = re.sub(r"\s*/\s*", " / ", txt)  # '21/ D' -> '21 / D'
        from collections import Counter
        mm = re.findall(r"(\d+(?:\.\d+)?)\s*/\s*([A-Za-z](?:\.\d+)?)", txt)
        if mm:
            (num, letter), _ = Counter(mm).most_common(1)[0]
            txt = f"{num} / {letter}"
        if not txt:
            flags.append({"cell": f"header point {k}", "issue": "khong OCR duoc ten diem"})
            txt = f"?{k}"
        if conf < 0.8:
            flags.append({"cell": f"header point {k}", "issue": f"ten diem conf thap {conf:.2f}: {txt!r}"})
        points.append(txt)
    out_rows = []
    for r in range(3, n_row):
        label, lconf = cells.get((r, 0), ("", 1.0))
        label = re.sub(r"\s+", " ", (label or "")).strip()
        # chuan hoa ten dong theo danh sach 26 dong chuan (OCR hay sai
        # chinh ta: 'ccnveyor', 'BC5A'...); chi nhan khi giong ro
        canon = _canonical_row(label)
        if canon and canon != label:
            flags.append({"cell": f"row {r}", "issue": f"ten dong OCR {label!r} -> chuan hoa {canon!r}"})
            label = canon
        if label and not canon:
            flags.append({"cell": f"row {r}", "issue": f"ten dong la: {label!r} (khong khop 26 dong chuan)"})
        sign_txt, _ = cells.get((r, 1), ("", 1.0))
        reversible = (sign_txt or "").strip() in ("+/-", "±", "+/- ")
        if not label:
            flags.append({"cell": f"row {r}", "issue": "khong OCR duoc ten dong tai"})
            continue
        values = {}
        for k, pt in enumerate(points):
            comp = {}
            for j, comp_name in enumerate(("Hx", "Hy", "Vz")):
                c = 2 + k * 3 + j
                raw, conf = cells.get((r, c), (None, 1.0))
                # dau '+/-' nam trong o (bang E-HOUSE): dong nay dao chieu
                if raw and str(raw).strip().startswith(("+/-", "-/+", "±")):
                    reversible = True
                val, kind, note = clean_num(raw) if raw is not None else (None, "blank", "o trong")
                if kind == "bad":
                    flags.append({"cell": f"{label} / {pt} / {comp_name}",
                                  "issue": note, "ocr": raw, "conf": round(conf, 2)})
                elif kind == "blank":
                    flags.append({"cell": f"{label} / {pt} / {comp_name}",
                                  "issue": "o trong (khong OCR duoc so)", "ocr": raw, "conf": round(conf, 2)})
                elif conf < 0.75:
                    flags.append({"cell": f"{label} / {pt} / {comp_name}",
                                  "issue": f"conf thap {conf:.2f}", "ocr": raw, "conf": round(conf, 2)})
                comp[comp_name] = {"raw": raw, "kind": kind, "value": val}
            values[pt] = comp
        out_rows.append({"name": label, "reversible": reversible, "values": values})
    return {"band": name, "page": band[0], "points": points,
            "n_grid_rows": n_row, "n_grid_cols": n_col,
            "rows": out_rows, "flags": flags}


def process_band(band, do_ocr=True):
    strip_path, _ = crop_strip(band[0], band)
    rows, cols, shape = detect_grid(strip_path)
    print(f"{band[1]}: strip {shape[1]}x{shape[0]}  grid {len(rows)-1} rows x {len(cols)-1} cols")
    items = ocr_strip(strip_path) if do_ocr else []
    print(f"  OCR: {len(items)} doan text")
    cells = assign_cells(items, rows, cols)
    table = parse_band(band, rows, cols, cells)
    print(f"  points: {table['points']}")
    print(f"  dong tai: {len(table['rows'])}  flags: {len(table['flags'])}")
    for f in table["flags"][:10]:
        print("   FLAG:", f)
    return table


def main():
    only = sys.argv[1:] or None
    results = {}
    if OUT_JSON.exists():
        results = json.loads(OUT_JSON.read_text(encoding="utf-8"))
    for band in BANDS:
        if only and band[1] not in only:
            continue
        table = process_band(band)
        results[band[1]] = table
        OUT_JSON.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  -> da luu {band[1]} vao {OUT_JSON}")
    print("DONE")


if __name__ == "__main__":
    main()
