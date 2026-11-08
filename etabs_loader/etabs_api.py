"""Ket noi ETABS qua COM API (comtypes) + ban Mock de test offline.

API that duoc (can doi chieu file .chm trong thu muc cai ETABS):
  - helper = comtypes.client.CreateObject('ETABSv1.Helper')
  - attach ETABS dang mo: helper.GetObject("CSI.ETABS.API.ETABSObject")
    hoac mo moi: helper.CreateObjectProgID("CSI.ETABS.API.ETABSObject")
  - SapModel.SetPresentUnits(6)  # 6 = kN_m_C (theo huong dan API)
  - SapModel.LoadPatterns.Add(name, load_type, self_weight_mult, add_load_case)
    voi LTYPE_OTHER = 8
  - SapModel.PointObj.SetLoadForce(point_name, load_pattern, [Fx,Fy,Fz,Mx,My,Mz])
  - SapModel.PointObj.GetNameList() / GetLabelFromName() / GetNameFromLabel()

CHUA XAC MINH tren ETABS that: ten ham GetSelected/Select, va cach tra
ret qua comtypes. Ma enum loai pattern DA doi chieu voi CSiAPIv1.dll
v22 that (2026-11-08). Neu ham nao bao loi tren may that, ghi lai thong
bao + version ETABS, app se sua theo dung .chm — khong doan them.
Xem HUONG_DAN_TEST muc 5.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .detector import PatternDef

# Ma loai pattern theo CSiAPIv1.eLoadPatternType — DA DOI CHIEU truc tiep
# voi CSiAPIv1.dll that tu ETABS v22 cua user (2026-11-08, bang chuong
# trinh dotnet doc enum tu DLL): Notional=12 (KHONG phai 9 — 9 la Move),
# Temperature=10 (CO ton tai), Rooflive=11 (KHONG phai 4 — 4 la ReduceLive).
# Ban truoc dung 9/4/8 sai 3 ma — da sua. Fallback Other=8 van giu.
LOAD_TYPE_CODE = {
    "Dead": 1, "SuperDead": 2, "Super Dead": 2,
    "Live": 3, "ReduceLive": 4, "Reduce Live": 4,
    "Seismic": 5, "Quake": 5, "Wind": 6, "Snow": 7, "Other": 8,
    "Move": 9, "Temperature": 10,
    "Rooflive": 11, "Roof Live": 11, "Notional": 12,
}


NEG_SUFFIX = "_NEG"


def _type_to_code(type_str) -> int:
    """Chuan hoa loai pattern (ten 'Seismic' hay ma so '5' tu .chm)
    ve ma int de tao pattern. Khong biet -> Other=8."""
    if type_str is None:
        return 8
    s = str(type_str).strip()
    if s.isdigit():
        return int(s)
    return LOAD_TYPE_CODE.get(s, 8)


_CODE_TO_NAME = {1: "Dead", 2: "Super Dead", 3: "Live", 4: "Reduce Live",
                 5: "Seismic", 6: "Wind", 7: "Snow", 8: "Other", 9: "Move",
                 10: "Temperature", 11: "Roof Live", 12: "Notional"}


def create_type_for(pattern_name: str, existing_patterns) -> int:
    """Ma loai de tao 1 pattern moi.
    Pattern _NEG (chieu am cua hang +/-) ke thua dung loai cua pattern
    goc trong model (EX_NEG <- EX 'Seismic'=5, NX_NEG <- NX 'Notional'=9);
    pattern khac hoac khong tim thay goc -> Other=8."""
    if pattern_name.endswith(NEG_SUFFIX):
        base = pattern_name[:-len(NEG_SUFFIX)]
        for p in existing_patterns:
            if p.name == base:
                return _type_to_code(p.type)
    return 8


@dataclass
class PointInfo:
    name: str  # UniqueName trong ETABS
    label: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class MockEtabs:
    """Mo phong ETABS de test offline (khong can ETABS/Windows).

    Seed pattern + diem lay tu anh user gui (29 pattern, diem 20/D...).
    """

    SEED_PATTERNS = [
        ("BC1", "Live", 0), ("BC2", "Live", 0), ("BT1", "Live", 0),
        ("BT2", "Live", 0), ("DLS", "Super Dead", 0), ("EX", "Seismic", 0),
        ("EY", "Seismic", 0), ("EZ", "Seismic", 0), ("F", "Live", 0),
        ("LL1", "Live", 0), ("LL2", "Live", 0), ("LL3", "Live", 0),
        ("LL4", "Live", 0), ("LL5", "Live", 0), ("LLR", "Roof Live", 0),
        ("NX", "Notional", 0), ("NY", "Notional", 0), ("SLL1", "Other", 0),
        ("SLL2", "Other", 0), ("SPL1", "Other", 0), ("SPL2", "Other", 0),
        ("SW", "Dead", 1), ("T", "Temperature", 0), ("WX-", "Wind", 0),
        ("WX+", "Wind", 0), ("WY-1", "Wind", 0), ("WY-2", "Wind", 0),
        ("WY+1", "Wind", 0), ("WY+2", "Wind", 0),
    ]

    def __init__(self):
        self.patterns = [PatternDef(n, "No", t, sw) for n, t, sw in self.SEED_PATTERNS]
        self.points = {f"{g} / {a}": PointInfo(name=f"{g} / {a}", label=f"{g} / {a}")
                       for g in ("20", "27") for a in ("D", "E")}
        self.assignments = []  # list[(joint, pattern, [6 gia tri])]
        self.selected = ["20 / D"]
        self.connected = True

    def list_patterns(self):
        return list(self.patterns)

    def pattern_names(self):
        return [p.name for p in self.patterns]

    def list_points(self):
        return list(self.points.values())

    def get_selected_points(self):
        return [self.points[s] for s in self.selected if s in self.points]

    def create_pattern(self, name, type_str="Other", type_code=None):
        if name in self.pattern_names():
            return False
        if type_code is not None:
            type_str = _CODE_TO_NAME.get(type_code, "Other")
        self.patterns.append(PatternDef(name, "No", type_str, 0))
        return True

    def assign_force(self, joint, pattern, values, replace=True):
        if joint not in self.points:
            raise EtabsError(f"Mock: khong co joint '{joint}' (co: {sorted(self.points)}).")
        if pattern not in self.pattern_names():
            raise EtabsError(f"Mock: khong co pattern '{pattern}'. Tick 'tu tao pattern' hoac match lai.")
        if replace:
            self.assignments = [a for a in self.assignments
                                if not (a[0] == joint and a[1] == pattern)]
        self.assignments.append((joint, pattern, list(values)))
        return True

    def get_assignment(self, joint, pattern):
        for j, p, v in self.assignments:
            if j == joint and p == pattern:
                return v
        return None

    def refresh_view(self):
        return True


class RealEtabs:
    """Ket noi ETABS that qua comtypes. Chi chay tren Windows co ETABS."""

    def __init__(self):
        self.helper = None
        self.etabs = None
        self.sap = None

    def connect(self, attach=True):
        try:
            import comtypes.client
        except ImportError as e:
            raise EtabsError("Chua cai comtypes — chay: pip install comtypes.") from e
        helper = comtypes.client.CreateObject("ETABSv1.Helper")
        helper = helper.QueryInterface(comtypes.gen.ETABSv1.cHelper)
        if attach:
            try:
                self.etabs = helper.GetObject("CSI.ETABS.API.ETABSObject")
            except Exception:
                self.etabs = None
        if self.etabs is None:
            self.etabs = helper.CreateObjectProgID("CSI.ETABS.API.ETABSObject")
            self.etabs.ApplicationStart()
        self.sap = self.etabs.SapModel
        # Don vi truyen qua API: kN, m, C (ma 6 theo huong dan API)
        try:
            self.sap.SetPresentUnits(6)
        except Exception:
            pass
        self.helper = helper
        return True

    def _ret(self, ret, what):
        if ret != 0:
            raise EtabsError(f"ETABS tra ret={ret} khi {what} (0 = OK). "
                             "Doi chieu 'CSI API ETABS v1.chm' trong thu muc cai ETABS.")
        return True

    def list_patterns(self):
        n, names = self.sap.LoadPatterns.GetNameList()
        out = []
        for nm in names or []:
            try:
                # GetLoadType chi tra 1 out (MyType) — comtypes tra thang
                # gia tri do (khong phai tuple 4 phan tu nhu ban cu ghi).
                res = self.sap.LoadPatterns.GetLoadType(nm)
                typ = res[-1] if isinstance(res, tuple) else res
            except Exception:
                typ = ""
            out.append(PatternDef(name=nm, type=str(typ)))
        return out

    def pattern_names(self):
        return [p.name for p in self.list_patterns()]

    def list_points(self):
        n, names = self.sap.PointObj.GetNameList()
        out = []
        for nm in names or []:
            try:
                # GetLabelFromName tra 2 out (Label, Story) — khong phai 4.
                res = self.sap.PointObj.GetLabelFromName(nm)
                label = res[0] if isinstance(res, tuple) else res
            except Exception:
                label = nm
            try:
                x, y, z = self.sap.PointObj.GetCoordCartesian(nm)[:3]
            except Exception:
                x = y = z = 0.0
            out.append(PointInfo(name=nm, label=label, x=x, y=y, z=z))
        return out

    def get_selected_points(self):
        # CSI API: SapModel.SelectObj.GetSelected() -> (n, ObjType[], ObjName[])
        # (thuoc tinh la SelectObj, khong phai Select; ObjectType 1 = point)
        n, types, names = self.sap.SelectObj.GetSelected()
        pts = {p.name: p for p in self.list_points()}
        out = []
        for t, nm in zip(types or [], names or []):
            if t == 1 and nm in pts:  # 1 = point object
                out.append(pts[nm])
        return out

    def create_pattern(self, name, type_str="Other", type_code=None):
        code = type_code if type_code is not None else LOAD_TYPE_CODE.get(type_str, 8)
        ret = self.sap.LoadPatterns.Add(name, code, 0, True)
        if ret != 0 and code != 8:
            ret = self.sap.LoadPatterns.Add(name, 8, 0, True)
        self._ret(ret, f"tao pattern '{name}' (type {type_str})")
        return True

    def assign_force(self, joint, pattern, values, replace=True):
        # PointObj.SetLoadForce(Name, LoadPat, Value[6], Replace, ItemType)
        # Value = [Fx, Fy, Fz, Mx, My, Mz]; Replace=True = ghi de len tai cu
        # cua cung pattern tai diem nay.
        try:
            ret = self.sap.PointObj.SetLoadForce(joint, pattern, list(values), replace)
        except TypeError:
            ret = self.sap.PointObj.SetLoadForce(joint, pattern, list(values))
        self._ret(ret, f"gan tai {pattern} tai joint '{joint}'")
        return True

    def refresh_view(self):
        try:
            self.sap.View.RefreshView()
        except Exception:
            pass
        return True
