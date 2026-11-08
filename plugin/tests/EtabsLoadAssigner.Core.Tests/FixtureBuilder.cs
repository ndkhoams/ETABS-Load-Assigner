using ClosedXML.Excel;

namespace EtabsLoadAssigner.Core.Tests;

/// <summary>
/// Tao fixture TONG HOP bang ClosedXML, mirror make_fixture.py ben repo app Python.
///
/// CANH BAO — day KHONG phai file that cua client: cac so duoc chep tay
/// tu anh screenshot, chi de test detector/assigner offline. Test tren
/// fixture nay la bang chung yeu; ket qua quyet dinh phai chay lai tren
/// file Excel that (xem chuong trinh parity o /tmp, khong nam trong repo).
///
/// Layout (giong anh LONG PHU BC-5):
///   row 1: ten diem o cot Hx (C, F, I, L)
///   row 2: Hx | Hy | Vz cho moi diem
///   row 3: [kN] (dong don vi — detector bo qua)
///   row 4..29: 26 dong tai (cot A = ten, cot B = "+/-" neu dao chieu)
///   sheet "Load Patterns": TABLE: Load Pattern Definitions (29 pattern)
/// </summary>
public static class FixtureBuilder
{
    public static readonly string[] Points = { "20 / D", "20 / E", "27 / D", "27 / E" };

    // (ten dong, +/-, {diem: (Hx, Hy, Vz)}) — so chep tu anh; diem 27 chi co
    // dong Dead loads doc duoc trong anh, cac dong khac de 0.
    public static readonly (string Name, string Sign, Dictionary<string, (double Hx, double Hy, object Vz)> Vals)[] Rows =
    {
        ("Dead loads", "", new() { ["20 / D"] = (0, -2, 19), ["20 / E"] = (0, 2, 19), ["27 / D"] = (0, -2, 23), ["27 / E"] = (0, 2, 23) }),
        ("Live load belt conveyor load BC-5A", "", new()),
        ("Live load belt conveyor load BC-5B", "", new()),
        ("Live load incrustation", "", new()),
        ("Live load walkway left side (5,0kN/m²)", "", new()),
        ("Live load walkway middle (5,0kN/m²)", "", new()),
        ("Live load walkway right side (5,0kN/m²)", "", new()),
        ("Live load platforms and stairs", "", new()),
        ("Live load roof (inacc.)", "", new() { ["20 / D"] = (0, -1, 21), ["20 / E"] = (0, 1, 21) }),
        ("Live load belt tension BC-5A max/min", "", new()),
        ("Live load belt tension BC-5B max/min", "", new()),
        ("Imperfektion X", "+/-", new() { ["20 / D"] = (-1, 0, 0), ["20 / E"] = (-1, 0, 0) }),
        ("Imperfektion Y", "+/-", new() { ["20 / D"] = (0, 0, -1), ["20 / E"] = (0, 0, 1) }),
        ("Friction +X", "+/-", new()),
        ("Wind +X", "", new() { ["20 / D"] = (1, 0, -1), ["20 / E"] = (1, -1, -1) }),
        ("Wind -X", "", new() { ["20 / D"] = (-1, 0, 1), ["20 / E"] = (-1, 1, 1) }),
        ("Wind +Y", "", new() { ["20 / D"] = (0, 7, -11), ["20 / E"] = (0, 6, "-3/+6") }),
        ("Wind -Y", "", new() { ["20 / D"] = (0, -6, "-3/+6"), ["20 / E"] = (0, -7, -11) }),
        ("Temperatur DT = 16°C", "+/-", new() { ["20 / D"] = (0, -1, 0), ["20 / E"] = (0, -1, 0) }),
        ("Earthquake X (LFP; 0,12g)", "+/-", new() { ["20 / D"] = (1, -1, 1), ["20 / E"] = (1, -1, -1) }),
        ("Earthquake Y (LFP; 0,12g)", "+/-", new() { ["20 / D"] = (0, 3, -3), ["20 / E"] = (0, 3, 3) }),
        ("Earthquake Z (LFP; 0,94g)", "+/-", new() { ["20 / D"] = (0, -1, 2), ["20 / E"] = (0, 1, 2) }),
        ("Special load overload belt BC-5A", "", new()),
        ("Special load overload belt BC-5B", "", new()),
        ("Live load Lifting jack #1 (service load 16 kN)", "", new()),
        ("Live load Lifting jack #2 (service load 16 kN)", "", new()),
    };

    public static readonly (string Name, string Auto, string Type, double Sw)[] Patterns =
    {
        ("BC1", "No", "Live", 0), ("BC2", "No", "Live", 0),
        ("BT1", "No", "Live", 0), ("BT2", "No", "Live", 0),
        ("DLS", "No", "Super Dead", 0), ("EX", "No", "Seismic", 0),
        ("EY", "No", "Seismic", 0), ("EZ", "No", "Seismic", 0),
        ("F", "No", "Live", 0), ("LL1", "No", "Live", 0),
        ("LL2", "No", "Live", 0), ("LL3", "No", "Live", 0),
        ("LL4", "No", "Live", 0), ("LL5", "No", "Live", 0),
        ("LLR", "No", "Roof Live", 0), ("NX", "No", "Notional", 0),
        ("NY", "No", "Notional", 0), ("SLL1", "No", "Other", 0),
        ("SLL2", "No", "Other", 0), ("SPL1", "No", "Other", 0),
        ("SPL2", "No", "Other", 0), ("SW", "No", "Dead", 1),
        ("T", "No", "Temperature", 0), ("WX-", "No", "Wind", 0),
        ("WX+", "No", "Wind", 0), ("WY-1", "No", "Wind", 0),
        ("WY-2", "No", "Wind", 0), ("WY+1", "No", "Wind", 0),
        ("WY+2", "No", "Wind", 0),
    };

    /// <summary>Build file .xlsx tam o thu muc cho truoc, tra ve duong dan.</summary>
    public static string Build(string path)
    {
        using var wb = new XLWorkbook();
        var ws = wb.Worksheets.Add("Foundation loads");
        ws.Cell(1, 1).Value = "LONG PHU BC-5 A/B";
        ws.Cell(2, 1).Value = "Foundation loads (action loads)";
        ws.Cell(3, 1).Value = "Tolerance +/- 20%";
        for (int k = 0; k < Points.Length; k++)
        {
            int c = 3 + k * 3; // cot C bat dau (A=ten, B=+/-, C..)
            ws.Cell(1, c).Value = Points[k];
            ws.Cell(2, c).Value = "Hx";
            ws.Cell(2, c + 1).Value = "Hy";
            ws.Cell(2, c + 2).Value = "Vz";
            ws.Cell(3, c).Value = "[kN]";
            ws.Cell(3, c + 1).Value = "[kN]";
            ws.Cell(3, c + 2).Value = "[kN]";
        }
        int r = 4;
        foreach (var (name, sign, vals) in Rows)
        {
            ws.Cell(r, 1).Value = name;
            ws.Cell(r, 2).Value = sign;
            for (int k = 0; k < Points.Length; k++)
            {
                int c = 3 + k * 3;
                var (hx, hy, vz) = vals.TryGetValue(Points[k], out var v) ? v : (0.0, 0.0, (object)0);
                ws.Cell(r, c).Value = hx;
                ws.Cell(r, c + 1).Value = hy;
                if (vz is string s)
                    ws.Cell(r, c + 2).Value = s;
                else
                    ws.Cell(r, c + 2).Value = Convert.ToDouble(vz);
            }
            r++;
        }
        ws.Cell(r + 1, 1).Value = "Note: Alle applied loads directly on concrete by client are not included in this table.";
        var ws2 = wb.Worksheets.Add("Load Patterns");
        ws2.Cell(1, 1).Value = "TABLE: Load Pattern Definitions";
        foreach (var (h, j) in new[] { ("Name", 1), ("Is Auto Load", 2), ("Type", 3), ("Self Weight Multiplier", 4), ("GUID", 5) })
            ws2.Cell(2, j).Value = h;
        for (int i = 0; i < Patterns.Length; i++)
        {
            var (nm, auto, typ, sw) = Patterns[i];
            ws2.Cell(i + 3, 1).Value = nm;
            ws2.Cell(i + 3, 2).Value = auto;
            ws2.Cell(i + 3, 3).Value = typ;
            ws2.Cell(i + 3, 4).Value = sw;
            ws2.Cell(i + 3, 5).Value = $"00000000-0000-4000-8000-{i + 1:000000000000}";
        }
        wb.SaveAs(path);
        return path;
    }
}
