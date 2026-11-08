"""Build danh sach gan tai tu bang da nhan dien + mapping.

Dau ra: list[Assignment] san sang dua vao ETABS (PointObj.SetLoadForce)
hoac vao MockEtabs de test offline. Khong tu y doi dau / doi pattern:
moi gia tri la, khoang, hang +/- deu ghi chu ro trong Assignment.notes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .detector import FoundationTable
from .mapping import AxisMapping, Profile, resolve_range


@dataclass
class Assignment:
    excel_point: str
    etabs_joint: str
    excel_row: str
    pattern: str
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0
    notes: str = ""
    negated: bool = False  # ban dao chieu cua hang +/-

    def values(self):
        return [self.fx, self.fy, self.fz, self.mx, self.my, self.mz]

    def is_zero(self):
        return all(v == 0 for v in self.values())


@dataclass
class BuildResult:
    assignments: list = field(default_factory=list)
    skipped: list = field(default_factory=list)  # (ly do, mo ta)
    warnings: list = field(default_factory=list)

    def totals_by_pattern(self):
        tot = {}
        for a in self.assignments:
            t = tot.setdefault(a.pattern, [0.0, 0.0, 0.0, 0])
            t[0] += a.fx
            t[1] += a.fy
            t[2] += a.fz
            t[3] += 1
        return tot


def build_assignments(table: FoundationTable, excel_point: str,
                      profile: Profile) -> BuildResult:
    """Gan tai cho 1 diem Excel (vd '20 / D') sang 1 joint ETABS."""
    res = BuildResult()
    if excel_point not in table.points:
        res.skipped.append(("diem", f"Diem '{excel_point}' khong co trong bang (co: {table.points})."))
        return res
    etabs_joint = profile.point_alias.get(excel_point, excel_point)
    axis = profile.axis
    errs = axis.validate()
    if errs:
        res.warnings.extend(errs)
        return res

    for row in table.rows:
        pattern = (profile.pattern_for(row.name) or "").strip()
        if not pattern:
            res.skipped.append(("chua match pattern", f"'{row.name}' o {excel_point}: chua gan pattern ETABS."))
            continue
        comp = row.values.get(excel_point, {})
        hx_lv, hy_lv, vz_lv = comp.get("Hx"), comp.get("Hy"), comp.get("Vz")
        if hx_lv is None or hy_lv is None or vz_lv is None:
            res.skipped.append(("thieu so", f"'{row.name}' o {excel_point}: thieu o Hx/Hy/Vz."))
            continue
        notes = []
        if row.reversible:
            notes.append("hang +/-, co the dao chieu")
        vals, ok = [], True
        for lv in (hx_lv, hy_lv, vz_lv):
            if lv.kind == "text":
                res.skipped.append(("o khong phai so", f"'{row.name}' o {excel_point}: o '{lv.raw}' khong phai so."))
                ok = False
                break
            if lv.kind == "blank":
                vals.append(0.0)
            elif lv.kind == "range":
                v, note = resolve_range(lv, profile.range_policy)
                if v is None:
                    res.skipped.append(("khoang", f"'{row.name}' o {excel_point}: {note}."))
                    ok = False
                    break
                vals.append(v)
                notes.append(note)
            else:
                vals.append(lv.value)
        if not ok:
            continue
        fx, fy, fz = axis.apply(vals[0], vals[1], vals[2])
        base = Assignment(excel_point=excel_point, etabs_joint=etabs_joint,
                          excel_row=row.name, pattern=pattern,
                          fx=fx, fy=fy, fz=fz,
                          notes="; ".join(notes))
        if profile.skip_zero_rows and base.is_zero():
            res.skipped.append(("dong 0", f"'{row.name}' o {excel_point}: ca 3 luc = 0, bo qua."))
            continue
        res.assignments.append(base)
        if row.reversible and profile.reversible_mode == "both":
            neg = Assignment(excel_point=excel_point, etabs_joint=etabs_joint,
                             excel_row=row.name, pattern=pattern + "_NEG",
                             fx=-fx, fy=-fy, fz=-fz, negated=True,
                             notes="ban dao chieu cua hang +/- (pattern _NEG)")
            if not (profile.skip_zero_rows and neg.is_zero()):
                res.assignments.append(neg)
                res.warnings.append(
                    f"'{row.name}': tao them pattern '{pattern}_NEG' cho chieu am — "
                    "nho kiem tra pattern nay co trong model khong.")
    return res


def preview_text(table: FoundationTable, excel_point: str, profile: Profile,
                 result: BuildResult) -> str:
    lines = [
        f"Diem Excel: {excel_point}  ->  Joint ETABS: {profile.point_alias.get(excel_point, excel_point)}",
        f"Phuong/chieu: {profile.axis.describe()}   (don vi kN, M = 0 — bang goc chi co luc)",
        f"So luong gan: {len(result.assignments)} | Bo qua: {len(result.skipped)} | Canh bao: {len(result.warnings)}",
        "",
        f"{'Pattern':<10} {'Fx':>8} {'Fy':>8} {'Fz':>8}   Nguon (dong Excel)",
    ]
    for a in result.assignments:
        extra = f"  [{a.notes}]" if a.notes else ""
        lines.append(f"{a.pattern:<10} {a.fx:8.2f} {a.fy:8.2f} {a.fz:8.2f}   {a.excel_row}{extra}")
    lines.append("")
    lines.append("Tong theo pattern:")
    for pat, (fx, fy, fz, n) in sorted(result.totals_by_pattern().items()):
        lines.append(f"  {pat:<10} Fx={fx:8.2f}  Fy={fy:8.2f}  Fz={fz:8.2f}  ({n} dong)")
    if result.skipped:
        lines.append("")
        lines.append("Da bo qua:")
        for kind, msg in result.skipped:
            lines.append(f"  - [{kind}] {msg}")
    if result.warnings:
        lines.append("")
        lines.append("Canh bao:")
        for w in result.warnings:
            lines.append(f"  ! {w}")
    return "\n".join(lines)
