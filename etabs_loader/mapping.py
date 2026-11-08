"""Mapping: phuong/chieu Hx-Hy-Vz -> ETABS global, match pattern,
va profile luu/tai cai dat (chuc nang 2, 3, 4).

Quy uoc mac dinh (suy tu so do toa do trong anh user gui):
  - So do ve: Hx mui ten sang trai, Hy len tren, "+z down".
  - ETABS global: +Z huong len. Nen Vz (duong khi huong xuong)
    -> Fz = -Vz.
  - Hx/Hy: dau + mac dinh giu nguyen (+1). Dau nay KHONG suy ra
    duoc tu anh — phai kiem tra 1 diem that (xem HUONG_DAN_TEST muc 4)
    roi dao dau trong bang neu can. App khong tu doan them.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from .detector import LoadValue

AXES = ("X", "Y", "Z")


@dataclass
class AxisMapping:
    hx_axis: str = "X"
    hx_sign: int = +1
    hy_axis: str = "Y"
    hy_sign: int = +1
    vz_axis: str = "Z"
    vz_sign: int = -1  # +z down (client) -> ETABS +Z up

    def validate(self) -> list:
        errs = []
        if sorted([self.hx_axis, self.hy_axis, self.vz_axis]) != ["X", "Y", "Z"]:
            errs.append("Hx/Hy/Vz phai anh xa sang 3 truc X, Y, Z khac nhau (khong trung truc).")
        for s in (self.hx_sign, self.hy_sign, self.vz_sign):
            if s not in (+1, -1):
                errs.append(f"Dau phai +1 hoac -1, nhan duoc {s}.")
        return errs

    def apply(self, hx: float, hy: float, vz: float):
        """Tra ve (Fx, Fy, Fz) theo truc ETABS."""
        out = {"X": 0.0, "Y": 0.0, "Z": 0.0}
        out[self.hx_axis] = self.hx_sign * hx
        out[self.hy_axis] = self.hy_sign * hy
        out[self.vz_axis] = self.vz_sign * vz
        return out["X"], out["Y"], out["Z"]

    def describe(self) -> str:
        def fmt(axis, sign):
            return f"{'+' if sign > 0 else '-'}{axis}"
        return f"Hx -> F{fmt(self.hx_axis, self.hx_sign)} | Hy -> F{fmt(self.hy_axis, self.hy_sign)} | Vz -> F{fmt(self.vz_axis, self.vz_sign)}"

    def to_dict(self):
        return {"hx_axis": self.hx_axis, "hx_sign": self.hx_sign,
                "hy_axis": self.hy_axis, "hy_sign": self.hy_sign,
                "vz_axis": self.vz_axis, "vz_sign": self.vz_sign}

    @classmethod
    def from_dict(cls, d):
        if not d:
            return cls()
        return cls(hx_axis=d.get("hx_axis", "X"), hx_sign=int(d.get("hx_sign", +1)),
                   hy_axis=d.get("hy_axis", "Y"), hy_sign=int(d.get("hy_sign", +1)),
                   vz_axis=d.get("vz_axis", "Z"), vz_sign=int(d.get("vz_sign", -1)))


def resolve_range(lv: LoadValue, policy: str = "max_abs"):
    """Giai quyet o '-3/+6'. Tra ve (gia_tri, ghi_chu)."""
    if lv.kind != "range":
        return lv.value, ""
    a, b = lv.vmin, lv.vmax
    if policy == "max_abs":
        v = a if abs(a) >= abs(b) else b
        return v, f"khoang {lv.raw} -> lay {v} (|.| lon nhat)"
    if policy == "max":
        return max(a, b), f"khoang {lv.raw} -> lay max {max(a, b)}"
    if policy == "min":
        return min(a, b), f"khoang {lv.raw} -> lay min {min(a, b)}"
    return None, f"khoang {lv.raw} -> bo qua theo cai dat"


# --- Goi y match pattern (CHI LA GOI Y, user chot trong bang) ---------
# Ten pattern ETABS lay tu bang 'Load Pattern Definitions' trong anh:
# BC1, BC2, BT1, BT2, DLS, EX, EY, EZ, F, LL1..LL5, LLR, NX, NY,
# SLL1, SLL2, SPL1, SPL2, SW, T, WX-, WX+, WY-1, WY-2, WY+1, WY+2.
# Cac goi y duoi day suy tu ten goi (BC=belt conveyor, BT=belt tension,
# NX/NY=notional/imperfection, F=friction...) — chua duoc user xac nhan.
SUGGESTED_MAP = {
    "dead loads": "DLS",
    "live load belt conveyor load bc-5a": "BC1",
    "live load belt conveyor load bc-5b": "BC2",
    "live load belt tension bc-5a max/min": "BT1",
    "live load belt tension bc-5b max/min": "BT2",
    "live load roof (inacc.)": "LLR",
    "imperfektion x": "NX",
    "imperfektion y": "NY",
    "friction +x": "F",
    "wind +x": "WX+",
    "wind -x": "WX-",
    "wind +y": "WY+1",
    "wind -y": "WY-1",
    "temperatur dt = 16°c": "T",
    "earthquake x (lfp; 0,12g)": "EX",
    "earthquake y (lfp; 0,12g)": "EY",
    "earthquake z (lfp; 0,94g)": "EZ",
    "live load walkway left side (5,0kn/m²)": "LL1",
    "live load walkway middle (5,0kn/m²)": "LL2",
    "live load walkway right side (5,0kn/m²)": "LL3",
    "live load platforms and stairs": "LL4",
    "live load lifting jack #1 (service load 16 kn)": "LL5",
}


def _norm_name(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def suggest_pattern(excel_name: str, available: list) -> str:
    """Goi y pattern ETABS cho 1 dong tai Excel. Tra ve '' neu khong chac."""
    if not available:
        return ""
    key = _norm_name(excel_name)
    if key in SUGGESTED_MAP and SUGGESTED_MAP[key] in available:
        return SUGGESTED_MAP[key]
    # cham diem theo token chung (vd 'wind +x' trung 'wx+')
    best, best_score = "", 0
    tokens = set(re.findall(r"[a-z0-9]+", key))
    for pat in available:
        ptokens = set(re.findall(r"[a-z0-9]+", pat.lower()))
        score = len(tokens & ptokens)
        if pat.lower() in key:
            score += 2
        if score > best_score:
            best, best_score = pat, score
    return best if best_score >= 1 else ""


@dataclass
class Profile:
    """Cai dat luu lai de gan diem moi khong phai lam lai (chuc nang 4)."""
    version: int = 1
    source_file: str = ""
    sheet: str = ""
    axis: AxisMapping = field(default_factory=AxisMapping)
    pattern_map: dict = field(default_factory=dict)  # ten dong Excel -> pattern ETABS
    point_alias: dict = field(default_factory=dict)  # diem Excel vd '20 / D' -> joint ETABS
    replace_existing: bool = True
    create_missing_pattern: bool = False
    reversible_mode: str = "plus_only"  # plus_only | both
    range_policy: str = "max_abs"  # max_abs | max | min | skip
    skip_zero_rows: bool = True

    def to_dict(self):
        return {"version": self.version, "source_file": self.source_file,
                "sheet": self.sheet, "axis": self.axis.to_dict(),
                "pattern_map": self.pattern_map, "point_alias": self.point_alias,
                "replace_existing": self.replace_existing,
                "create_missing_pattern": self.create_missing_pattern,
                "reversible_mode": self.reversible_mode,
                "range_policy": self.range_policy,
                "skip_zero_rows": self.skip_zero_rows}

    @classmethod
    def from_dict(cls, d):
        p = cls()
        p.version = d.get("version", 1)
        p.source_file = d.get("source_file", "")
        p.sheet = d.get("sheet", "")
        p.axis = AxisMapping.from_dict(d.get("axis"))
        p.pattern_map = dict(d.get("pattern_map", {}))
        p.point_alias = dict(d.get("point_alias", {}))
        p.replace_existing = bool(d.get("replace_existing", True))
        p.create_missing_pattern = bool(d.get("create_missing_pattern", False))
        p.reversible_mode = d.get("reversible_mode", "plus_only")
        p.range_policy = d.get("range_policy", "max_abs")
        p.skip_zero_rows = bool(d.get("skip_zero_rows", True))
        return p

    def save(self, path: str):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: str):
        with open(path, encoding="utf-8") as f:
            return cls.from_dict(json.load(f))
