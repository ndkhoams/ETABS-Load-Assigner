using Xunit;

namespace EtabsLoadAssigner.Core.Tests;

/// <summary>Port cua tests/test_assigner.py (phan assigner/mapping/profile/mock) — cap nhat theo model 2 cot (user chot 08/11).</summary>
public sealed class AssignerTests : IDisposable
{
    private readonly string _fixture;
    private readonly string _tmpDir;

    public AssignerTests()
    {
        _tmpDir = Path.Combine(Path.GetTempPath(), "ela-tests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tmpDir);
        _fixture = FixtureBuilder.Build(Path.Combine(_tmpDir, "longphu_bc5_synthetic.xlsx"));
    }

    public void Dispose()
    {
        try { Directory.Delete(_tmpDir, recursive: true); } catch { /* best effort */ }
    }

    // Match 2 cot: trai = gia tri 1 / gia tri don, phai = gia tri 2 (chi khi o co 2 gia tri).
    // Cot "+/-" cua bang KHONG anh huong den gia tri (user chot 08/11).
    private static Profile TestProfile()
    {
        var p = new Profile();
        p.PatternMap = new Dictionary<string, RowPattern>
        {
            ["Dead loads"] = new() { Left = "DLS" },
            ["Live load roof (inacc.)"] = new() { Left = "LLR" },
            ["Imperfektion X"] = new() { Left = "NX", Right = "NX_NEG" },
            ["Imperfektion Y"] = new() { Left = "NY", Right = "NY_NEG" },
            ["Wind +X"] = new() { Left = "WX+" },
            ["Wind -X"] = new() { Left = "WX-" },
            ["Wind +Y"] = new() { Left = "WY+1" },
            ["Wind -Y"] = new() { Left = "WY-1", Right = "WY+2" },
            ["Temperatur DT = 16°C"] = new() { Left = "T", Right = "T_NEG" },
            ["Earthquake X (LFP; 0,12g)"] = new() { Left = "EX", Right = "EX_NEG" },
            ["Earthquake Y (LFP; 0,12g)"] = new() { Left = "EY", Right = "EY_NEG" },
            ["Earthquake Z (LFP; 0,94g)"] = new() { Left = "EZ", Right = "EZ_NEG" },
        };
        return p;
    }

    [Fact]
    public void Assigner_AssignsMoments_WhenTableHasMoments()
    {
        // Bang co mo men: mo men duoc gan kem theo luc, cung pattern, cung
        // phuong/chieu (Mx theo truc Hx, My theo Hy, Mz theo Vz — Vz -> -Z
        // nen Mz doi dau, Mx/My giu dau). Bang khong co mo men thi Mx=My=Mz=0.
        var grid = new List<List<object?>>
        {
            new() { "LONG PHU BC-5", "", "20 / D", "", "", "", "", "" },
            new() { "Foundation loads", "", "Hx", "Hy", "Vz", "Mx", "My", "Mz" },
            new() { "", "", "[kN]", "[kN]", "[kN]", "[kN·m]", "[kN·m]", "[kN·m]" },
            new() { "Dead loads", "", 0, -2, 19, 5, -3, 2 },
        };
        var t = Detector.DetectFromGrid(grid, "test", "Foundation loads");
        var p = new Profile();
        p.PatternMap = new Dictionary<string, RowPattern>
        {
            ["Dead loads"] = new() { Left = "DLS" },
        };
        var res = Assigner.BuildAssignments(t, "20 / D", "J1", p);
        Assert.Empty(res.Skipped);
        var a = Assert.Single(res.Assignments);
        Assert.Equal("DLS", a.Pattern);
        Assert.Equal(-2, a.Fy);
        Assert.Equal(-19, a.Fz);
        Assert.Equal(5, a.Mx);
        Assert.Equal(-3, a.My);
        Assert.Equal(-2, a.Mz); // Mz doi dau theo Vz -> -Z
        Assert.Equal(new[] { 0.0, -2.0, -19.0, 5.0, -3.0, -2.0 }, a.Values());
    }

    [Fact]
    public void Assigner_NoMoments_WhenTableHasForcesOnly()
    {
        // Bang chi co luc: Mx/My/Mz = 0 (khong doi hanh vi cu).
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", TestProfile());
        var byPat = res.Assignments.ToDictionary(a => a.Pattern);
        Assert.Equal(0, byPat["DLS"].Mx);
        Assert.Equal(0, byPat["DLS"].My);
        Assert.Equal(0, byPat["DLS"].Mz);
    }

    [Fact]
    public void Axis_Default_VzDown_ToMinusZ()
    {
        var ax = new AxisMapping(); // mac dinh Vz -> -Z
        Assert.Equal((0, -2, -19), ax.Apply(0, -2, 19));
        Assert.Equal((1, 0, 1), ax.Apply(1, 0, -1));
    }

    [Fact]
    public void Axis_Validate_RejectsDuplicateAxes()
    {
        var ax = new AxisMapping { HyAxis = "X" }; // Hx va Hy cung X
        Assert.NotEmpty(ax.Validate());
        Assert.Empty(new AxisMapping().Validate());
    }

    [Fact]
    public void Assigner_20D_DeadAndWind()
    {
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", TestProfile());
        var byPat = res.Assignments.ToDictionary(a => a.Pattern);
        // Dead: Hy=-2 -> Fy=-2, Vz=19 -> Fz=-19
        Assert.Equal(-2, byPat["DLS"].Fy);
        Assert.Equal(-19, byPat["DLS"].Fz);
        // Wind +Y: Hy=7, Vz=-11 -> Fy=7, Fz=+11
        Assert.Equal(7, byPat["WY+1"].Fy);
        Assert.Equal(11, byPat["WY+1"].Fz);
        // Hang 0 bi bo qua, hang chua match bi skip (khong crash).
        Assert.Contains(res.Skipped, s => s.Reason == "chua match pattern");
    }

    [Fact]
    public void Assigner_ReversibleColumn_Ignored_SingleValue()
    {
        // Cot "+/-" cua bang KHONG anh huong den gia tri gan (user chot 08/11):
        // hang +/- co so don chi gan 1 gia tri (cot trai), khong tach -V/+V.
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", TestProfile());
        var byPat = res.Assignments.ToDictionary(a => a.Pattern);
        // Imperfektion X V=(-1,0,0): chi NX = (-1,0,0), khong co NX_NEG.
        Assert.Equal(-1, byPat["NX"].Fx);
        Assert.Equal("trai", byPat["NX"].Side);
        Assert.DoesNotContain(res.Assignments, a => a.Pattern == "NX_NEG");
        // Imperfektion Y V=(0,0,-1): chi NY, Fz = +1 (Vz -> -Z), khong co NY_NEG.
        Assert.Equal(1, byPat["NY"].Fz);
        Assert.DoesNotContain(res.Assignments, a => a.Pattern == "NY_NEG");
        // Earthquake X V=(1,-1,1): chi EX = (1,-1,-1), khong co EX_NEG.
        Assert.Equal((1, -1, -1), (byPat["EX"].Fx, byPat["EX"].Fy, byPat["EX"].Fz));
        Assert.DoesNotContain(res.Assignments, a => a.Pattern == "EX_NEG");
        // Temperatur V=(0,-1,0): chi T, khong co T_NEG.
        Assert.Equal((0, -1, 0), (byPat["T"].Fx, byPat["T"].Fy, byPat["T"].Fz));
        Assert.DoesNotContain(res.Assignments, a => a.Pattern == "T_NEG");
    }

    [Fact]
    public void Assigner_Range_FirstSecond()
    {
        // O khoang "-3/+6": cot trai nhan gia tri 1 (-3), cot phai nhan gia tri 2 (+6).
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", TestProfile());
        var wy = res.Assignments.Where(a => a.ExcelRow == "Wind -Y").ToList();
        Assert.Equal(2, wy.Count);
        var left = wy.Single(a => a.Side == "trai");
        var right = wy.Single(a => a.Side == "phai");
        Assert.Equal("WY-1", left.Pattern);
        Assert.Equal("WY+2", right.Pattern);
        // Wind -Y 20/D: Hy=-6, Vz=-3/+6 -> trai (0,-6,+3), phai (0,-6,-6) (Vz -> -Z).
        Assert.Equal((0, -6, 3), (left.Fx, left.Fy, left.Fz));
        Assert.Equal((0, -6, -6), (right.Fx, right.Fy, right.Fz));
    }

    [Fact]
    public void Assigner_Range_FirstSecond_NotMinMax()
    {
        // Khoang "67/-71": gia tri 1 = 67 (lon hon), gia tri 2 = -71 — KHONG phai min/max.
        var t = new FoundationTable();
        t.Points.Add("20 / D");
        var row = new FoundationRow { Name = "Wind +Y" };
        row.Values["20 / D"] = new Dictionary<string, LoadValue>
        {
            ["Hx"] = new LoadValue { Raw = "0", Kind = LoadValueKind.Number, Value = 0 },
            ["Hy"] = new LoadValue { Raw = "0", Kind = LoadValueKind.Number, Value = 0 },
            ["Vz"] = new LoadValue { Raw = "67/-71", Kind = LoadValueKind.Range, VMin = 67, VMax = -71 },
        };
        t.Rows.Add(row);
        var p = new Profile();
        p.PatternMap["Wind +Y"] = new RowPattern { Left = "WY+1", Right = "WY+2" };
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", p);
        Assert.Equal(2, res.Assignments.Count);
        var left = res.Assignments.Single(a => a.Side == "trai");
        var right = res.Assignments.Single(a => a.Side == "phai");
        Assert.Equal("WY+1", left.Pattern);
        Assert.Equal("WY+2", right.Pattern);
        // Vz -> -Z: trai Fz = -67 (gia tri 1), phai Fz = +71 (gia tri 2).
        Assert.Equal((0, 0, -67), (left.Fx, left.Fy, left.Fz));
        Assert.Equal((0, 0, 71), (right.Fx, right.Fy, right.Fz));
    }

    [Fact]
    public void Assigner_TwoColumns_Count()
    {
        // 12 dong co luc (cot trai) + 1 ban cot phai (o khoang Wind -Y Vz "-3/+6") = 13.
        // 6 hang +/- (Imperfektion X/Y, Temperatur, Earthquake X/Y/Z) chi gan 1 gia tri — cot "+/-" khong tach.
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", TestProfile());
        Assert.Equal(13, res.Assignments.Count);
        Assert.Equal(12, res.Assignments.Count(a => a.Side == "trai"));
        Assert.Equal(1, res.Assignments.Count(a => a.Side == "phai"));
    }

    [Fact]
    public void Assigner_RightPatternMissing_WarnsOnlyLeftAssigned()
    {
        // Dong co o 2 gia tri (Wind -Y Vz "-3/+6") nhung chua chon pattern cot phai: chi gan cot trai + canh bao.
        var t = Detector.DetectExcel(_fixture);
        var p = TestProfile();
        p.PatternMap["Wind -Y"] = new RowPattern { Left = "WY-1", Right = "" };
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", p);
        Assert.Contains(res.Assignments, a => a.Pattern == "WY-1");
        Assert.DoesNotContain(res.Assignments, a => a.Pattern == "WY+2");
        Assert.Contains(res.Warnings, w => w.Contains("Wind -Y") && w.Contains("cột phải"));
    }

    [Fact]
    public void Assigner_UnknownPoint_Skipped()
    {
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "99 / Z", "99 / Z", TestProfile());
        Assert.Empty(res.Assignments);
        Assert.Contains(res.Skipped, s => s.Reason == "diem");
    }

    [Fact]
    public void Assigner_MissingJoint_Skipped()
    {
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "", TestProfile());
        Assert.Empty(res.Assignments);
        Assert.Contains(res.Skipped, s => s.Reason == "diem");
    }

    [Fact]
    public void Profile_PatternFor_CaseInsensitive()
    {
        // Profile vi du luu key chu thuong, assigner dung ten goc — phai khop.
        var p = new Profile();
        p.PatternMap["dead loads"] = new RowPattern { Left = "DLS" };
        Assert.Equal("DLS", p.PatternFor("Dead loads").Left);
        Assert.Equal("DLS", p.PatternFor("DEAD LOADS").Left);
        Assert.Equal("", p.PatternFor("Khong co").Left);
        Assert.Equal("", p.PatternFor("Khong co").Right);
    }

    [Fact]
    public void Profile_PatternFor_OldSingleColumn_LoadsAsLeft()
    {
        // Profile cu luu pattern_map dang {"Dead loads": "DLS"} (chuoi) — doc len thanh cot trai.
        var p = new Profile();
        string json = "{\"version\":1,\"pattern_map\":{\"Dead loads\":\"DLS\"}}";
        using var doc = System.Text.Json.JsonDocument.Parse(json);
        var p2 = Profile.FromDictionary(doc.RootElement);
        Assert.Equal("DLS", p2.PatternFor("Dead loads").Left);
        Assert.Equal("", p2.PatternFor("Dead loads").Right);
    }

    [Fact]
    public void SuggestPattern()
    {
        var avail = new MockEtabs().PatternNames();
        Assert.Equal("DLS", Mapping.SuggestPattern("Dead loads", avail));
        Assert.Equal("WX+", Mapping.SuggestPattern("Wind +X", avail));
        Assert.Equal("EY", Mapping.SuggestPattern("Earthquake Y (LFP; 0,12g)", avail));
        Assert.Equal("NX", Mapping.SuggestPattern("Imperfektion X", avail));
        Assert.Equal("", Mapping.SuggestPattern("Dead loads", Array.Empty<string>()));
    }

    [Fact]
    public void SuggestPatternOpposite()
    {
        var avail = new List<string> { "EX", "EX_NEG", "WX+", "WX-", "WY+1", "WY-1", "DLS" };
        Assert.Equal("EX_NEG", Mapping.SuggestPatternOpposite("EX", avail));
        Assert.Equal("WX-", Mapping.SuggestPatternOpposite("WX+", avail));
        Assert.Equal("WY-1", Mapping.SuggestPatternOpposite("WY+1", avail));
        Assert.Equal("", Mapping.SuggestPatternOpposite("DLS", avail));
        Assert.Equal("", Mapping.SuggestPatternOpposite("", avail));
    }

    [Fact]
    public void MockAssign_Roundtrip()
    {
        var t = Detector.DetectExcel(_fixture);
        var mock = new MockEtabs();
        // User tu tao pattern _NEG trong ETABS truoc (tool khong tu tao) — mo phong bang CreatePattern tren mock.
        foreach (string neg in new[] { "NX_NEG", "NY_NEG", "EX_NEG", "EY_NEG", "EZ_NEG", "T_NEG" })
            mock.CreatePattern(neg, typeCode: PatternTypes.CreateTypeFor(neg, mock.ListPatterns()));
        var p = TestProfile();
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", p);
        foreach (var a in res.Assignments)
            mock.AssignForce(a.EtabsJoint, a.Pattern, a.Values());
        var v = mock.GetAssignment("20 / D", "DLS");
        Assert.NotNull(v);
        Assert.Equal(new double[] { 0, -2, -19, 0, 0, 0 }, v);
        // Imperfektion X chi gan 1 gia tri (-1,0,0) vao NX; NX_NEG khong duoc gan (cot "+/-" khong tach).
        Assert.Equal(new double[] { -1, 0, 0, 0, 0, 0 }, mock.GetAssignment("20 / D", "NX"));
        Assert.Null(mock.GetAssignment("20 / D", "NX_NEG"));
        // Ghi de: gan lai chi giu 1 ban.
        mock.AssignForce("20 / D", "DLS", new double[] { 0, -2, -19, 0, 0, 0 }, replace: true);
        Assert.Single(mock.Assignments, a => a.Pattern == "DLS");
    }

    [Fact]
    public void MockAssign_MissingPattern_Throws()
    {
        // Tool khong tu tao pattern: gan vao pattern chua co trong model thi loi (user phai tao truoc trong ETABS).
        var mock = new MockEtabs();
        Assert.Throws<EtabsError>(() => mock.AssignForce("20 / D", "KHONG_CO", new double[] { 0, 0, 1, 0, 0, 0 }));
    }

    [Fact]
    public void MockEtabs_ClearJointLoads_RemovesAllPatterns()
    {
        // Ghi de (user chot 08/11): xoá trắng MỌI tải tại joint trước khi gán
        // mới — cả tải không có trong file Excel (vd tải gán tay bằng pattern
        // khác) cũng bị xoá, để điểm chỉ còn tải do plugin nhập vào.
        var mock = new MockEtabs();
        mock.AssignForce("20 / D", "DLS", new double[] { 0, -2, -19, 0, 0, 0 });
        mock.AssignForce("20 / D", "LLR", new double[] { 0, -1, -21, 0, 0, 0 });
        mock.AssignForce("20 / D", "EX", new double[] { 1, -1, -1, 0, 0, 0 });
        // 1 tải ở joint khác — không được xoá.
        mock.AssignForce("27 / E", "DLS", new double[] { 0, 0, -5, 0, 0, 0 });
        // DeleteLoadForce 1 pattern: chỉ xoá pattern đó.
        Assert.True(mock.DeleteLoadForce("20 / D", "LLR"));
        Assert.Null(mock.GetAssignment("20 / D", "LLR"));
        Assert.NotNull(mock.GetAssignment("20 / D", "DLS"));
        Assert.False(mock.DeleteLoadForce("20 / D", "LLR")); // đã xoá rồi -> false
        // ClearJointLoads: xoá hết tải còn lại tại joint, joint khác còn nguyên.
        int cleared = mock.ClearJointLoads("20 / D");
        Assert.Equal(2, cleared);
        Assert.Null(mock.GetAssignment("20 / D", "DLS"));
        Assert.Null(mock.GetAssignment("20 / D", "EX"));
        Assert.NotNull(mock.GetAssignment("27 / E", "DLS"));
        Assert.Equal(0, mock.ClearJointLoads("20 / D")); // đã trắng -> 0
    }

    [Fact]
    public void CreateTypeFor_InheritsBaseType()
    {
        // Port cua create_type_for() (Python). Ma so theo enum eLoadPatternType
        // trong CSiAPIv1.dll that (v22) — KHAC ban Python o Notional:
        // Python ghi 9 (9 la Move!), DLL ghi Notional=12.
        var existing = new MockEtabs().ListPatterns();
        Assert.Equal(5, PatternTypes.CreateTypeFor("EX_NEG", existing));  // Seismic
        Assert.Equal(5, PatternTypes.CreateTypeFor("EY_NEG", existing));
        Assert.Equal(5, PatternTypes.CreateTypeFor("EZ_NEG", existing));
        Assert.Equal(12, PatternTypes.CreateTypeFor("NX_NEG", existing)); // Notional
        Assert.Equal(12, PatternTypes.CreateTypeFor("NY_NEG", existing));
        Assert.Equal(6, PatternTypes.CreateTypeFor("WX+_NEG", existing)); // Wind
        Assert.Equal(10, PatternTypes.CreateTypeFor("T_NEG", existing));  // Temperature (co trong enum v22)
        Assert.Equal(8, PatternTypes.CreateTypeFor("DLS", existing));      // khong phai _NEG
        Assert.Equal(8, PatternTypes.CreateTypeFor("ZZ_NEG", existing));   // khong tim thay goc
        Assert.Equal(8, PatternTypes.CreateTypeFor("WX_NEG", existing));   // goc "WX" khong ton tai (chi co WX+/WX-)
    }

    [Fact]
    public void CreateTypeFor_TypeToCode()
    {
        Assert.Equal(8, PatternTypes.TypeToCode(null));
        Assert.Equal(5, PatternTypes.TypeToCode("5"));
        Assert.Equal(5, PatternTypes.TypeToCode("Seismic"));
        Assert.Equal(12, PatternTypes.TypeToCode("Notional"));
        Assert.Equal(8, PatternTypes.TypeToCode("Khong biet"));
    }

    [Fact]
    public void MockEtabs_CreatePattern_WithTypeCode()
    {
        var mock = new MockEtabs();
        Assert.True(mock.CreatePattern("EX_NEG", typeCode: 5));
        Assert.Equal("Seismic", mock.ListPatterns().Single(p => p.Name == "EX_NEG").Type);
        Assert.True(mock.CreatePattern("NX_NEG", typeCode: 12));
        Assert.Equal("Notional", mock.ListPatterns().Single(p => p.Name == "NX_NEG").Type);
        Assert.True(mock.CreatePattern("T_NEG", typeCode: 8));
        Assert.Equal("Other", mock.ListPatterns().Single(p => p.Name == "T_NEG").Type);
        Assert.False(mock.CreatePattern("EX_NEG", typeCode: 5)); // da co
    }

    [Fact]
    public void Profile_SaveLoad_Roundtrip()
    {
        var p = TestProfile();
        p.Axis.VzSign = -1;
        string f = Path.Combine(_tmpDir, "prof.json");
        p.Save(f);
        var p2 = Profile.Load(f);
        Assert.Equal("DLS", p2.PatternMap["Dead loads"].Left);
        Assert.Equal("NX_NEG", p2.PatternMap["Imperfektion X"].Right);
        Assert.Equal("WY+2", p2.PatternMap["Wind -Y"].Right);
        Assert.Equal(-1, p2.Axis.VzSign);
    }

    [Fact]
    public void PreviewText_ContainsAssignmentsAndTotals()
    {
        var t = Detector.DetectExcel(_fixture);
        var p = TestProfile();
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", p);
        string text = Assigner.PreviewText(t, "20 / D", "20 / D", p, res);
        Assert.Contains("DLS", text);
        Assert.Contains("WY+1", text);
        Assert.Contains("Tổng theo pattern:", text);
    }
}
