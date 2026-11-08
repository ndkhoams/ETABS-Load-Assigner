"""Giao dien Tkinter — ETABS Load Assigner v0.1.

5 tab tuong ung 5 chuc nang user yeu cau:
  1. File & bang (tu dong nhan dien tu Excel/PDF)
  2. Diem gan tai
  3. Phuong & chieu Hx/Hy/Vz -> ETABS global
  4. Match pattern (dong Excel <-> pattern ETABS)
  5. Preview & gan vao ETABS
Thanh profile o tren: Luu / Tai cai dat de gan diem moi khong lam lai.
"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from .assigner import build_assignments, preview_text
from .detector import detect_file
from .etabs_api import EtabsError, MockEtabs, create_type_for
from .mapping import AxisMapping, Profile, suggest_pattern


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("ETABS Load Assigner v0.1 — Gan tai mong tu Excel/PDF")
        self.geometry("1050x720")
        self.table = None
        self.profile = Profile()
        self.etabs = MockEtabs()
        self.etabs_mode = tk.StringVar(value="mock")
        self.current_point = tk.StringVar(value="")
        self.file_path = tk.StringVar(value="")
        self.status = tk.StringVar(value="Chua import file. Che do offline (Mock ETABS) — test khong can ETABS.")
        self._pattern_vars = {}   # excel row name -> StringVar (combobox)
        self._alias_vars = {}     # excel point -> StringVar (entry)
        self._axis_vars = {}
        self._build_ui()

    # ---------------- UI ----------------
    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="Chon file Excel/PDF...", command=self.choose_file).pack(side="left")
        ttk.Entry(top, textvariable=self.file_path, width=45).pack(side="left", padx=6)
        ttk.Label(top, text="Sheet:").pack(side="left")
        self.sheet_var = tk.StringVar(value="")
        self.sheet_combo = ttk.Combobox(top, textvariable=self.sheet_var, width=22, state="readonly")
        self.sheet_combo.pack(side="left", padx=4)
        self.sheet_combo.bind("<<ComboboxSelected>>", lambda e: self.detect())
        ttk.Button(top, text="Nhan dien bang", command=self.detect).pack(side="left")
        ttk.Button(top, text="Tai profile...", command=self.load_profile).pack(side="left", padx=6)
        ttk.Button(top, text="Luu profile...", command=self.save_profile).pack(side="left")
        ttk.Label(self, textvariable=self.status, wraplength=1000, foreground="#555").pack(fill="x", padx=8)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=4)
        self.tab_file = ttk.Frame(nb, padding=8)
        self.tab_point = ttk.Frame(nb, padding=8)
        self.tab_axis = ttk.Frame(nb, padding=8)
        self.tab_match = ttk.Frame(nb, padding=8)
        self.tab_assign = ttk.Frame(nb, padding=8)
        nb.add(self.tab_file, text="1. File & bang")
        nb.add(self.tab_point, text="2. Diem gan tai")
        nb.add(self.tab_axis, text="3. Phuong & chieu")
        nb.add(self.tab_match, text="4. Match pattern")
        nb.add(self.tab_assign, text="5. Preview & gan")
        self._build_tab_file()
        self._build_tab_point()
        self._build_tab_axis()
        self._build_tab_match()
        self._build_tab_assign()

    def _build_tab_file(self):
        ttk.Label(self.tab_file, text="Bang tai mong da nhan dien (chi doc — sua o file goc roi nhan dien lai):").pack(anchor="w")
        self.tree = ttk.Treeview(self.tab_file, show="headings")
        self.tree.pack(fill="both", expand=True, pady=4)
        self.file_info = tk.Text(self.tab_file, height=6, wrap="word")
        self.file_info.pack(fill="x")

    def _build_tab_point(self):
        ttk.Label(self.tab_point, text="Chon diem Excel can gan (moi lan gan 1 diem; profile giu nguyen cho diem sau):").pack(anchor="w")
        row = ttk.Frame(self.tab_point)
        row.pack(fill="x", pady=4)
        self.point_combo = ttk.Combobox(row, textvariable=self.current_point, state="readonly", width=20)
        self.point_combo.pack(side="left")
        ttk.Button(row, text="Lay diem dang chon trong ETABS", command=self.use_selected_point).pack(side="left", padx=6)
        ttk.Label(row, text="(ETABS that: chon joint trong model truoc roi bam nut. Offline: dung diem mock.)").pack(side="left")
        ttk.Label(self.tab_point, text="Anh xa diem Excel -> Joint ETABS (mac dinh giong ten; sua neu joint trong model dat ten khac):").pack(anchor="w", pady=(8, 0))
        self.alias_frame = ttk.Frame(self.tab_point)
        self.alias_frame.pack(fill="x")
        mode = ttk.Frame(self.tab_point)
        mode.pack(fill="x", pady=8)
        ttk.Radiobutton(mode, text="Offline — Mock ETABS (test, khong can ETABS)", variable=self.etabs_mode, value="mock", command=self.switch_mode).pack(anchor="w")
        ttk.Radiobutton(mode, text="ETABS that dang mo (COM API, Windows)", variable=self.etabs_mode, value="real", command=self.switch_mode).pack(anchor="w")
        ttk.Button(mode, text="Ket noi ETABS", command=self.connect_etabs).pack(anchor="w", pady=4)
        self.etabs_info = tk.Text(self.tab_point, height=8, wrap="word")
        self.etabs_info.pack(fill="both", expand=True)

    def _build_tab_axis(self):
        ttk.Label(self.tab_axis, text="Anh xa phuong/chieu — so do goc: Hx mui ten sang trai, Hy len tren, '+z down' (Vz duong khi huong xuong).", wraplength=950).pack(anchor="w")
        ttk.Label(self.tab_axis, text="ETABS global +Z huong len, nen mac dinh Vz -> -Z. Dau Hx/Hy phai kiem tra 1 diem that truoc khi gan hang loat (xem HUONG_DAN_TEST muc 4).", wraplength=950, foreground="#a33").pack(anchor="w")
        self.axis_frame = ttk.Frame(self.tab_axis)
        self.axis_frame.pack(fill="x", pady=8)
        for excel_axis in ("Hx", "Hy", "Vz"):
            r = ttk.Frame(self.axis_frame)
            r.pack(fill="x", pady=3)
            ttk.Label(r, text=f"{excel_axis}  ->  ETABS", width=16).pack(side="left")
            tgt = tk.StringVar(value=getattr(self.profile.axis, f"{excel_axis.lower()}_axis"))
            sign = tk.StringVar(value="+" if getattr(self.profile.axis, f"{excel_axis.lower()}_sign") > 0 else "-")
            ttk.Combobox(r, textvariable=tgt, values=["X", "Y", "Z"], width=5, state="readonly").pack(side="left")
            ttk.Combobox(r, textvariable=sign, values=["+", "-"], width=4, state="readonly").pack(side="left", padx=6)
            self._axis_vars[excel_axis] = (tgt, sign)
            tgt.trace_add("write", lambda *a: self.update_axis_example())
            sign.trace_add("write", lambda *a: self.update_axis_example())
        self.axis_example = tk.StringVar(value="")
        ttk.Label(self.tab_axis, textvariable=self.axis_example, wraplength=950).pack(anchor="w", pady=6)
        ttk.Button(self.tab_axis, text="Cap nhat vi du", command=self.update_axis_example).pack(anchor="w")
        self.update_axis_example()

    def _build_tab_match(self):
        bar = ttk.Frame(self.tab_match)
        bar.pack(fill="x")
        ttk.Button(bar, text="Goi y tu dong tat ca", command=self.auto_suggest_all).pack(side="left")
        ttk.Label(bar, text="  Goi y theo ten (BC=belt conveyor, BT=belt tension, NX/NY=notional...) — CHI LA GOI Y, ban chot lai tung dong.").pack(side="left")
        opts = ttk.Frame(self.tab_match)
        opts.pack(fill="x", pady=6)
        self.create_missing_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opts, text="Tu tao pattern chua co trong model", variable=self.create_missing_var).pack(side="left")
        self.reversible_var = tk.StringVar(value="both")
        ttk.Label(opts, text="  Hang +/-:").pack(side="left")
        ttk.Combobox(opts, textvariable=self.reversible_var, values=["plus_only", "both"], width=12, state="readonly").pack(side="left")
        ttk.Label(opts, text="(plus_only = chi chieu +, both = them pattern _NEG chieu am)").pack(side="left")
        self.range_var = tk.StringVar(value="max_abs")
        ttk.Label(opts, text="  O khoang '-3/+6':").pack(side="left")
        ttk.Combobox(opts, textvariable=self.range_var, values=["max_abs", "max", "min", "skip"], width=10, state="readonly").pack(side="left")
        self.match_frame = ttk.Frame(self.tab_match)
        self.match_frame.pack(fill="both", expand=True)
        self.match_canvas = tk.Canvas(self.match_frame)
        self.match_scroll = ttk.Scrollbar(self.match_frame, orient="vertical", command=self.match_canvas.yview)
        self.match_inner = ttk.Frame(self.match_canvas)
        self.match_inner.bind("<Configure>", lambda e: self.match_canvas.configure(scrollregion=self.match_canvas.bbox("all")))
        self.match_canvas.create_window((0, 0), window=self.match_inner, anchor="nw")
        self.match_canvas.configure(yscrollcommand=self.match_scroll.set)
        self.match_canvas.pack(side="left", fill="both", expand=True)
        self.match_scroll.pack(side="right", fill="y")

    def _build_tab_assign(self):
        bar = ttk.Frame(self.tab_assign)
        bar.pack(fill="x")
        ttk.Button(bar, text="Xem preview", command=self.show_preview).pack(side="left")
        ttk.Button(bar, text="GAN VAO ETABS", command=self.assign).pack(side="left", padx=6)
        ttk.Button(bar, text="Xuat preview (.txt)", command=self.export_preview).pack(side="left")
        self.replace_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(bar, text="Ghi de tai cu cung pattern tai diem nay", variable=self.replace_var).pack(side="left", padx=6)
        self.preview = tk.Text(self.tab_assign, wrap="none", font=("Consolas", 10))
        self.preview.pack(fill="both", expand=True, pady=4)

    # ---------------- logic ----------------
    def _sync_profile_from_ui(self):
        for excel_axis in ("Hx", "Hy", "Vz"):
            tgt, sign = self._axis_vars[excel_axis]
            setattr(self.profile.axis, f"{excel_axis.lower()}_axis", tgt.get())
            setattr(self.profile.axis, f"{excel_axis.lower()}_sign", +1 if sign.get() == "+" else -1)
        self.profile.pattern_map = {k: v.get() for k, v in self._pattern_vars.items()}
        self.profile.point_alias = {k: v.get().strip() for k, v in self._alias_vars.items()}
        self.profile.create_missing_pattern = self.create_missing_var.get()
        self.profile.reversible_mode = self.reversible_var.get()
        self.profile.range_policy = self.range_var.get()
        self.profile.replace_existing = self.replace_var.get()

    def choose_file(self):
        p = filedialog.askopenfilename(filetypes=[("Excel/PDF", "*.xlsx *.pdf"), ("Excel", "*.xlsx"), ("PDF", "*.pdf")])
        if p:
            self.file_path.set(p)
            self.sheet_var.set("")
            if p.lower().endswith((".xlsx", ".xlsm")):
                try:
                    from .detector import list_sheets
                    self.sheet_combo["values"] = list_sheets(p)
                except Exception:
                    self.sheet_combo["values"] = []
            else:
                self.sheet_combo["values"] = []
            self.detect()

    def detect(self):
        path = self.file_path.get().strip()
        if not path or not os.path.exists(path):
            messagebox.showwarning("Chua chon file", "Chon file Excel (.xlsx) hoac PDF truoc.")
            return
        try:
            sheet = self.sheet_var.get().strip() or None
            self.table = detect_file(path, sheet=sheet)
        except Exception as e:
            messagebox.showerror("Khong doc duoc file", str(e))
            return
        # nap danh sach sheet (ca khi mo file bang cach khac, khong qua Chon file)
        if path.lower().endswith((".xlsx", ".xlsm")):
            try:
                from .detector import list_sheets
                self.sheet_combo["values"] = list_sheets(path)
            except Exception:
                pass
        self.profile.source_file = path
        self.profile.sheet = self.table.sheet
        if self.table.sheet and not self.sheet_var.get():
            self.sheet_var.set(self.table.sheet)
        t = self.table
        self.status.set(f"Da nhan dien: {len(t.points)} diem, {len(t.rows)} dong tai, {len(t.patterns)} pattern (sheet: {t.sheet}).")
        # Treeview
        cols = ["Load"]
        for p in t.points:
            cols += [f"{p} Hx", f"{p} Hy", f"{p} Vz"]
        self.tree["columns"] = cols
        for c in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=90 if c != "Load" else 320, anchor="center" if c != "Load" else "w")
        self.tree.delete(*self.tree.get_children())
        for r in t.rows:
            vals = [r.name + ("  (+/-)" if r.reversible else "")]
            for p in t.points:
                for comp in ("Hx", "Hy", "Vz"):
                    vals.append(r.values.get(p, {}).get(comp).raw if r.values.get(p, {}).get(comp) else "")
            self.tree.insert("", "end", values=vals)
        info = [f"Tieu de: {t.title or '(khong doc duoc)'}",
                f"Diem: {', '.join(t.points)}",
                f"Pattern trong file ({len(t.patterns)}): " + ", ".join(p.name for p in t.patterns[:40])]
        if t.warnings:
            info.append("Canh bao nhan dien:")
            info += [f"  ! {w}" for w in t.warnings]
        self.file_info.delete("1.0", "end")
        self.file_info.insert("end", "\n".join(info))
        # Point tab
        self.point_combo["values"] = t.points
        if t.points and not self.current_point.get():
            self.current_point.set(t.points[0])
        for w in self.alias_frame.winfo_children():
            w.destroy()
        self._alias_vars = {}
        for p in t.points:
            r = ttk.Frame(self.alias_frame)
            r.pack(fill="x", pady=2)
            ttk.Label(r, text=p, width=12).pack(side="left")
            v = tk.StringVar(value=self.profile.point_alias.get(p, p))
            ttk.Entry(r, textvariable=v, width=25).pack(side="left")
            ttk.Label(r, text="(joint ETABS)").pack(side="left")
            self._alias_vars[p] = v
        self.refresh_match_tab()
        self.update_axis_example()

    def refresh_match_tab(self):
        for w in self.match_inner.winfo_children():
            w.destroy()
        self._pattern_vars = {}
        if not self.table:
            return
        available = self.etabs.pattern_names()
        # neu file co bang pattern rieng, uu tien hien thi ca pattern do
        file_pats = [p.name for p in self.table.patterns]
        choices = [""] + sorted(set(available) | set(file_pats))
        for r in self.table.rows:
            rowf = ttk.Frame(self.match_inner)
            rowf.pack(fill="x", pady=2)
            ttk.Label(rowf, text=r.name + ("  (+/-)" if r.reversible else ""), width=48, anchor="w").pack(side="left")
            cur = self.profile.pattern_for(r.name) or suggest_pattern(r.name, available)
            v = tk.StringVar(value=cur)
            ttk.Combobox(rowf, textvariable=v, values=choices, width=14).pack(side="left")
            self._pattern_vars[r.name] = v

    def auto_suggest_all(self):
        if not self.table:
            return
        available = self.etabs.pattern_names()
        for r in self.table.rows:
            self._pattern_vars[r.name].set(suggest_pattern(r.name, available))
        self.status.set("Da goi y tu dong — kiem tra lai tung dong truoc khi gan.")

    def update_axis_example(self):
        self._sync_profile_from_ui() if self.table else None
        ax = AxisMapping(
            hx_axis=self._axis_vars["Hx"][0].get(), hx_sign=+1 if self._axis_vars["Hx"][1].get() == "+" else -1,
            hy_axis=self._axis_vars["Hy"][0].get(), hy_sign=+1 if self._axis_vars["Hy"][1].get() == "+" else -1,
            vz_axis=self._axis_vars["Vz"][0].get(), vz_sign=+1 if self._axis_vars["Vz"][1].get() == "+" else -1)
        errs = ax.validate()
        fx, fy, fz = ax.apply(1, -2, 19)
        self.axis_example.set(
            f"Hien tai: {ax.describe()}\n"
            f"Vi du — Dead loads diem 20/D (Hx=0, Hy=-2, Vz=19) -> Fx={fx:.0f}, Fy={fy:.0f}, Fz={fz:.0f} kN"
            + (f"\nLOI: {'; '.join(errs)}" if errs else "  (Vz=19 huong xuong -> Fz am la dung neu +z down)."))

    def switch_mode(self):
        if self.etabs_mode.get() == "mock":
            self.etabs = MockEtabs()
            self.status.set("Che do offline (Mock ETABS).")
            self.refresh_match_tab()

    def connect_etabs(self):
        if self.etabs_mode.get() == "mock":
            self.etabs = MockEtabs()
            self.etabs_info.delete("1.0", "end")
            self.etabs_info.insert("end", "Mock ETABS: 29 pattern (BC1...WY+2), diem 20/D, 20/E, 27/D, 27/E.\n")
            return
        try:
            from .etabs_api import RealEtabs
            conn = RealEtabs()
            conn.connect(attach=True)
            self.etabs = conn
            pats = conn.pattern_names()
            pts = conn.list_points()
            self.etabs_info.delete("1.0", "end")
            self.etabs_info.insert("end", f"Da ket noi ETABS: {len(pats)} pattern, {len(pts)} point.\nPattern: {', '.join(pats[:30])}")
            self.status.set(f"Da ket noi ETABS that: {len(pats)} pattern.")
            self.refresh_match_tab()
        except Exception as e:
            messagebox.showerror("Khong ket noi duoc ETABS", str(e))

    def use_selected_point(self):
        try:
            sel = self.etabs.get_selected_points()
        except Exception as e:
            messagebox.showerror("Loi", str(e))
            return
        if not sel:
            messagebox.showinfo("Chua chon diem", "Chon 1 joint trong ETABS truoc (hoac o che do Mock, diem dang chon la '20 / D').")
            return
        p = sel[0]
        self.status.set(f"Diem dang chon trong ETABS: label='{p.label}' name='{p.name}'. Nhap ten nay vao cot Joint ETABS o diem Excel tuong ung.")
        messagebox.showinfo("Diem dang chon", f"Label: {p.label}\nName: {p.name}\nToa do: ({p.x}, {p.y}, {p.z})")

    def _current_result(self):
        self._sync_profile_from_ui()
        if not self.table:
            messagebox.showwarning("Chua co bang", "Import file truoc.")
            return None, None
        point = self.current_point.get()
        if not point:
            messagebox.showwarning("Chua chon diem", "Chon diem Excel o tab 2.")
            return None, None
        res = build_assignments(self.table, point, self.profile)
        return point, res

    def show_preview(self):
        point, res = self._current_result()
        if res is None:
            return
        self.preview.delete("1.0", "end")
        self.preview.insert("end", preview_text(self.table, point, self.profile, res))

    def assign(self):
        point, res = self._current_result()
        if res is None:
            return
        if not res.assignments:
            messagebox.showwarning("Khong co gi de gan", "Preview trong: chua match pattern hoac toan dong 0.")
            return
        if not messagebox.askyesno("Xac nhan gan tai",
                                   f"Gan {len(res.assignments)} tai vao joint "
                                   f"'{self.profile.point_alias.get(point, point)}'?\n"
                                   f"Pattern: {', '.join(sorted(set(a.pattern for a in res.assignments)))}"):
            return
        # tao pattern thieu (neu tick) — pattern _NEG ke thua loai cua
        # pattern goc (EX_NEG <- EX 'Seismic'), khong phai tat ca Other.
        missing = [p for p in sorted(set(a.pattern for a in res.assignments))
                   if p not in self.etabs.pattern_names()]
        if missing:
            if self.profile.create_missing_pattern:
                existing = self.etabs.list_patterns()
                for p in missing:
                    try:
                        self.etabs.create_pattern(
                            p, type_code=create_type_for(p, existing))
                    except Exception as e:
                        messagebox.showerror("Khong tao duoc pattern", f"{p}: {e}")
                        return
            else:
                messagebox.showerror("Thieu pattern trong model",
                                     "Pattern chua co trong ETABS: " + ", ".join(missing) +
                                     "\nTick 'Tu tao pattern...' o tab 4, hoac tao tay trong ETABS roi gan lai.")
                return
        errs = []
        for a in res.assignments:
            try:
                self.etabs.assign_force(a.etabs_joint, a.pattern, a.values(),
                                        replace=self.profile.replace_existing)
            except Exception as e:
                errs.append(f"{a.pattern}@{a.etabs_joint}: {e}")
        try:
            self.etabs.refresh_view()
        except Exception:
            pass
        if errs:
            messagebox.showerror("Gan loi mot phan", "\n".join(errs))
        else:
            messagebox.showinfo("Xong", f"Da gan {len(res.assignments)} tai vao joint '{res.assignments[0].etabs_joint}'.")
        self.show_preview()

    def export_preview(self):
        point, res = self._current_result()
        if res is None:
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")])
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(preview_text(self.table, point, self.profile, res))
            self.status.set(f"Da xuat preview: {p}")

    def save_profile(self):
        self._sync_profile_from_ui()
        p = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Profile JSON", "*.json")])
        if p:
            self.profile.save(p)
            self.status.set(f"Da luu profile: {p} — lan sau Tai profile nay roi chi doi diem gan.")

    def load_profile(self):
        p = filedialog.askopenfilename(filetypes=[("Profile JSON", "*.json")])
        if not p:
            return
        try:
            self.profile = Profile.load(p)
        except Exception as e:
            messagebox.showerror("Khong doc duoc profile", str(e))
            return
        # dua len UI
        for excel_axis in ("Hx", "Hy", "Vz"):
            tgt, sign = self._axis_vars[excel_axis]
            tgt.set(getattr(self.profile.axis, f"{excel_axis.lower()}_axis"))
            sign.set("+" if getattr(self.profile.axis, f"{excel_axis.lower()}_sign") > 0 else "-")
        self.create_missing_var.set(self.profile.create_missing_pattern)
        self.reversible_var.set(self.profile.reversible_mode)
        self.range_var.set(self.profile.range_policy)
        self.replace_var.set(self.profile.replace_existing)
        if self.table:
            self.refresh_match_tab()
            for name, v in self._pattern_vars.items():
                if self.profile.pattern_for(name):
                    v.set(self.profile.pattern_for(name))
            for pt, v in self._alias_vars.items():
                if pt in self.profile.point_alias:
                    v.set(self.profile.point_alias[pt])
        self.status.set(f"Da tai profile: {p} (file goc: {self.profile.source_file}).")


def run():
    app = App()
    app.mainloop()
