"""Detector: tu dong loc / nhan dien bang tai mong (foundation loads)
tu file Excel (.xlsx) hoac PDF.

Cung mot ham `detect_from_grid` dung cho ca 2 duong (Excel va PDF)
de khong lech nhau — theo skill parallel_variant_sweep.

Dang bang nhan duoc (anh user gui — LONG PHU BC-5 A/B):
    LONG PHU BC-5 A/B |   20 / D    |   20 / E    | ...
    Foundation loads (action loads) | Hx | Hy | Vz | Hx | Hy | Vz | ...
    Tolerance +/- 20%                | [kN] ... (dong don vi)
    Dead loads                |      | 0 | -2 | 19 | 0 | 2 | 19 | ...
    Live load belt conveyor... |      | ...
    Imperfektion X            | +/-  | -1 | 0 | 0 | ...
    Wind +Y                   |      | 0 | 7 | -11 | 0 | 6 | -3/+6 | ...

Va bang phu (thuong o sheet ben canh / cung sheet phia phai):
    TABLE: Load Pattern Definitions
    Name | Is Auto Load | Type | Self Weight Multiplier | GUID
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

COMPONENTS = ("Hx", "Hy", "Vz")
_RANGE_RE = re.compile(r"^\s*([+-]?\d+(?:[.,]\d+)?)\s*/\s*([+-])\s*(\d+(?:[.,]\d+)?)\s*$")
_NUM_RE = re.compile(r"^[+-]?\d+(?:[.,]\d+)?$")


def _norm(v) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _num(s: str):
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


@dataclass
class LoadValue:
    """Mot o gia tri trong bang: so, khoang '-3/+6', hoac trong."""
    raw: str = ""
    kind: str = "blank"  # number | range | blank | text
    value: float | None = None
    vmin: float | None = None
    vmax: float | None = None

    def is_zero(self) -> bool:
        return self.kind == "number" and self.value == 0


def parse_cell(raw) -> LoadValue:
    if raw is None:
        return LoadValue(raw="", kind="blank")
    if isinstance(raw, (int, float)):
        return LoadValue(raw=str(raw), kind="number", value=float(raw))
    s = _norm(raw)
    if s in ("", "-", "--", "—", "n/a", "N/A"):
        return LoadValue(raw=s, kind="blank")
    # o viet '+/- 1' / '-/+ 0' (vd bang 90/D.1): gia tri dao chieu,
    # lay do lon; dau +/- goc giu trong raw de nguoi doc thay
    if s.startswith(("+/-", "-/+", "±")):
        s = s[3:].strip() if s.startswith(("+/-", "-/+")) else s[1:].strip()
        n = _num(s)
        if n is not None:
            return LoadValue(raw=str(raw).strip(), kind="number", value=n)
    m = _RANGE_RE.match(s)
    if m:
        a = _num(m.group(1))
        b = _num(m.group(2) + m.group(3))
        if a is not None and b is not None:
            return LoadValue(raw=s, kind="range", vmin=a, vmax=b)
    n = _num(s)
    if n is not None:
        return LoadValue(raw=s, kind="number", value=n)
    return LoadValue(raw=s, kind="text")


@dataclass
class FoundationRow:
    name: str
    reversible: bool = False  # cot "+/-" — tai co the dao chieu
    values: dict = field(default_factory=dict)  # point -> {"Hx": LoadValue, ...}

    def is_all_zero(self) -> bool:
        for comp_vals in self.values.values():
            for lv in comp_vals.values():
                if lv.kind == "number" and lv.value != 0:
                    return False
                if lv.kind == "range" and (lv.vmin != 0 or lv.vmax != 0):
                    return False
        return True


@dataclass
class PatternDef:
    name: str
    is_auto: str = ""
    type: str = ""
    self_weight: float = 0.0
    guid: str = ""


@dataclass
class FoundationTable:
    title: str = ""
    points: list = field(default_factory=list)  # vd ["20 / D", "20 / E"]
    rows: list = field(default_factory=list)  # list[FoundationRow]
    patterns: list = field(default_factory=list)  # list[PatternDef]
    source: str = ""
    sheet: str = ""
    warnings: list = field(default_factory=list)

    def point_values(self, point: str, row_name: str):
        for r in self.rows:
            if r.name == row_name:
                return r.values.get(point)
        return None


def _is_component_cell(v) -> bool:
    return _norm(v) in COMPONENTS


def _find_component_header(grid):
    """Tra ve (row_idx, col_idx_cua_Hx_dau_tien) cua dong tieu de Hx/Hy/Vz,
    hoac None. Dong nay phai co >= 2 nhom Hx-Hy-Vz."""
    for i, row in enumerate(grid):
        hits = [j for j, c in enumerate(row) if _is_component_cell(c)]
        if len(hits) < 3:
            continue
        # kiem tra co it nhat 1 nhom Hx,Hy,Vz lien tiep
        seq = [_norm(row[j]) for j in hits]
        if "Hx" in seq and "Hy" in seq and "Vz" in seq:
            return i, hits[0]
    return None


def _find_pattern_table(grid):
    """Tim bang 'Load Pattern Definitions' trong grid, tra ve list[PatternDef]."""
    patterns = []
    for i, row in enumerate(grid):
        cells = [_norm(c) for c in row]
        if any("Load Pattern Definitions" in c for c in cells):
            # dong tieu de cot o 1-2 dong sau
            for j in range(i + 1, min(i + 4, len(grid))):
                hdr = [_norm(c) for c in grid[j]]
                if "Name" in hdr and "Type" in hdr:
                    name_c = hdr.index("Name")
                    type_c = hdr.index("Type")
                    sw_c = hdr.index("Self Weight Multiplier") if "Self Weight Multiplier" in hdr else None
                    guid_c = hdr.index("GUID") if "GUID" in hdr else None
                    auto_c = hdr.index("Is Auto Load") if "Is Auto Load" in hdr else None
                    for r in grid[j + 1:]:
                        nm = _norm(r[name_c]) if name_c < len(r) else ""
                        if not nm:
                            continue
                        if nm in ("Name",):
                            continue
                        sw = 0.0
                        if sw_c is not None and sw_c < len(r):
                            sw = _num(_norm(r[sw_c])) or 0.0
                        patterns.append(PatternDef(
                            name=nm,
                            is_auto=_norm(r[auto_c]) if auto_c is not None and auto_c < len(r) else "",
                            type=_norm(r[type_c]) if type_c < len(r) else "",
                            self_weight=sw,
                            guid=_norm(r[guid_c]) if guid_c is not None and guid_c < len(r) else "",
                        ))
                    return patterns
            return patterns
    return patterns


def detect_from_grid(grid, source: str = "", sheet: str = "") -> FoundationTable:
    """Nhan dien bang tai mong tu mot grid (list[list]) — dung chung
    cho Excel (openpyxl) va PDF (pdfplumber extract_tables)."""
    table = FoundationTable(source=source, sheet=sheet)
    table.patterns = _find_pattern_table(grid)
    found = _find_component_header(grid)
    if not found:
        table.warnings.append(
            "Khong tim thay dong tieu de Hx/Hy/Vz trong file. "
            "Kiem tra lai: bang can co cac cot Hx, Hy, Vz (moi diem 3 cot).")
        return table
    hdr_row, first_hx_col = found

    # --- dong ten diem: dong ngay tren dong Hx/Hy/Vz, doc ten o cot Hx ---
    points, point_cols = [], []
    # tim nhom 3 cot: bat dau tu first_hx_col, moi nhom cach nhau 3 cot
    # (co the co cot ten tai / cot +/- chen truoc, nen quet tu Hx dau tien)
    j = first_hx_col
    point_row = grid[hdr_row - 1] if hdr_row >= 1 else []
    title_row = grid[hdr_row - 2] if hdr_row >= 2 else []
    while j + 2 < len(grid[hdr_row]) + 2:
        row_vals = grid[hdr_row]
        if j >= len(row_vals):
            break
        trio = [_norm(row_vals[k]) if k < len(row_vals) else "" for k in (j, j + 1, j + 2)]
        if trio != ["Hx", "Hy", "Vz"]:
            # nhom lech (co the co cot trong) — dich sang phai 1 cot, thu toi da 2 lan
            shifted = False
            for d in (1, 2):
                trio2 = [_norm(row_vals[k]) if k < len(row_vals) else "" for k in (j + d, j + d + 1, j + d + 2)]
                if trio2 == ["Hx", "Hy", "Vz"]:
                    j += d
                    trio = trio2
                    shifted = True
                    break
            if not shifted:
                break
        name = _norm(point_row[j]) if j < len(point_row) else ""
        if not name:
            name = f"Point {len(points) + 1}"
            table.warnings.append(f"Khong doc duoc ten diem o cot {j + 1}, tam dat '{name}'.")
        points.append(name)
        point_cols.append(j)
        j += 3
    if not points:
        table.warnings.append("Tim thay dong Hx/Hy/Vz nhung khong tach duoc diem nao.")
        return table
    table.points = points

    # --- tieu de bang: cac dong tren va ngay dong Hx (cot A thuong chua tieu de) ---
    for r in grid[max(0, hdr_row - 3):hdr_row + 1]:
        for c in r:
            if "Foundation loads" in _norm(c):
                table.title = _norm(c)
                break

    # --- dong du lieu: bat dau sau dong Hx/Hy/Vz, bo dong don vi [kN] ---
    i = hdr_row + 1
    if i < len(grid) and any("[kN]" in _norm(c) for c in grid[i]):
        i += 1
    while i < len(grid):
        row = grid[i]
        i += 1
        if not row:
            continue
        first = _norm(row[0]) if len(row) > 0 else ""
        if not first:
            continue
        low = first.lower()
        if low.startswith("note:") or low.startswith("note") and "applied loads" in low:
            break
        if "foundation loads" in low or "long phu" in low:
            break  # bang moi (vd diem 27/D o duoi trong cung sheet)
        if first in ("Hx", "Hy", "Vz"):
            continue
        # cot +/- : thuong la cot thu 2 (index 1), hoac ngay sau ten tai
        reversible = any(_norm(c) in ("+/-", "±", "+/- ") for c in row[:3])
        vals = {}
        for p, col in zip(points, point_cols):
            comp = {}
            for k, comp_name in enumerate(COMPONENTS):
                cell = row[col + k] if col + k < len(row) else None
                comp[comp_name] = parse_cell(cell)
            vals[p] = comp
        table.rows.append(FoundationRow(name=first, reversible=reversible, values=vals))
    if not table.rows:
        table.warnings.append("Nhan duoc diem nhung khong doc duoc dong tai nao.")
    return table


def list_sheets(path: str) -> list:
    """Liet ke ten sheet trong file Excel (de user chon bang can nhap
    khi file co nhieu bang — moi bang 1 sheet)."""
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    return list(wb.sheetnames)


def detect_excel(path: str, sheet: str | None = None) -> FoundationTable:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True)
    best = None
    for ws in wb.worksheets:
        if sheet is not None and ws.title != sheet:
            continue
        grid = [[c.value for c in row] for row in ws.iter_rows()]
        t = detect_from_grid(grid, source=path, sheet=ws.title)
        # uu tien bang co ca diem + dong tai; gop pattern table tu moi sheet
        if best is None:
            best = t
        elif len(t.rows) > len(best.rows):
            t.patterns = best.patterns + t.patterns
            best = t
        else:
            best.patterns = best.patterns + t.patterns
    if best is None:
        return FoundationTable(source=path, warnings=["File Excel khong co sheet nao."])
    # neu chi dinh sheet: van gop bang pattern tu cac sheet con lai
    if sheet is not None:
        for ws in wb.worksheets:
            if ws.title == sheet:
                continue
            grid = [[c.value for c in row] for row in ws.iter_rows()]
            best.patterns = best.patterns + _find_pattern_table(grid)
    return best


def detect_pdf(path: str) -> FoundationTable:
    try:
        import pdfplumber
    except ImportError as e:
        raise RuntimeError(
            "Chua cai pdfplumber — chay: pip install pdfplumber. "
            "Neu van muon dung ngay, gui file Excel thay cho PDF.") from e
    best = None
    with pdfplumber.open(path) as pdf:
        for pno, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables() or []
            for ti, raw in enumerate(tables):
                grid = [[c for c in row] for row in raw]
                t = detect_from_grid(grid, source=path, sheet=f"page {pno} table {ti + 1}")
                if t.rows and (best is None or len(t.rows) > len(best.rows)):
                    if best is not None:
                        t.patterns = best.patterns + t.patterns
                    best = t
                elif best is not None:
                    best.patterns = best.patterns + t.patterns
    if best is None:
        return FoundationTable(source=path, warnings=[
            "Khong tach duoc bang nao tu PDF (pdfplumber extract_tables tra ve rong). "
            "File PDF nay co the la anh scan — gui file Excel goc de gan dung."])
    return best


def detect_file(path: str, sheet: str | None = None) -> FoundationTable:
    low = path.lower()
    if low.endswith((".xlsx", ".xlsm")):
        return detect_excel(path, sheet=sheet)
    if low.endswith(".pdf"):
        return detect_pdf(path)
    if low.endswith(".xls"):
        raise RuntimeError("File .xls cu khong doc duoc bang openpyxl — luu lai thanh .xlsx roi import.")
    raise RuntimeError(f"Khong ho tro dinh dang file: {path} (chi .xlsx va .pdf).")
