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

    // Match 2 cot: trai = gia tri nho / gia tri don, phai = gia tri lon (chi khi co +/-).
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
    public void Assigner_Reversible_TwoColumns_LeftNegRightPos()
    {
        // Hang +/-: cot trai nhan -V (gia tri nho), cot phai nhan +V (gia tri lon).
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", TestProfile());
        var byPat = res.Assignments.ToDictionary(a => a.Pattern);
        // Imperfektion X V=(-1,0,0): trai -V=(1,0,0) -> NX; phai +V=(-1,0,0) -> NX_NEG.
        Assert.Equal(1, byPat["NX"].Fx);
        Assert.Equal("trai", byPat["NX"].Side);
        Assert.Equal(-1, byPat["NX_NEG"].Fx);
        Assert.Equal("phai", byPat["NX_NEG"].Side);
        // Imperfektion Y V=(0,0,-1): trai -V=(0,0,1) -> Fz=-1 (Vz -> -Z); phai +V=(0,0,-1) -> Fz=+1.
        Assert.Equal(-1, byPat["NY"].Fz);
        Assert.Equal(1, byPat["NY_NEG"].Fz);
        // Earthquake X V=(1,-1,1): trai -V=(-1,1,-1) -> Fx=-1, Fy=1, Fz=1; phai +V=(1,-1,1) -> Fx=1, Fy=-1, Fz=-1.
        Assert.Equal((-1, 1, 1), (byPat["EX"].Fx, byPat["EX"].Fy, byPat["EX"].Fz));
        Assert.Equal((1, -1, -1), (byPat["EX_NEG"].Fx, byPat["EX_NEG"].Fy, byPat["EX_NEG"].Fz));
    }

    [Fact]
    public void Assigner_Range_SplitsMinMax()
    {
        // O khoang "-3/+6": cot trai nhan min (-3), cot phai nhan max (+6).
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
    public void Assigner_TwoColumns_Count()
    {
        // 12 dong co luc (cot trai) + 7 ban cot phai (6 hang +/- + 1 o khoang Wind -Y) = 19.
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", TestProfile());
        Assert.Equal(19, res.Assignments.Count);
        Assert.Equal(12, res.Assignments.Count(a => a.Side == "trai"));
        Assert.Equal(7, res.Assignments.Count(a => a.Side == "phai"));
    }

    [Fact]
    public void Assigner_RightPatternMissing_WarnsOnlyLeftAssigned()
    {
        // Dong +/- nhung chua chon pattern cot phai: chi gan cot trai + canh bao.
        var t = Detector.DetectExcel(_fixture);
        var p = TestProfile();
        p.PatternMap["Imperfektion X"] = new RowPattern { Left = "NX", Right = "" };
        var res = Assigner.BuildAssignments(t, "20 / D", "20 / D", p);
        Assert.Contains(res.Assignments, a => a.Pattern == "NX");
        Assert.DoesNotContain(res.Assignments, a => a.Pattern == "NX_NEG");
        Assert.Contains(res.Warnings, w => w.Contains("Imperfektion X") && w.Contains("cột phải"));
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
        Assert.Equal(new double[] { -1, 0, 0, 0, 0, 0 }, mock.GetAssignment("20 / D", "NX_NEG"));
        Assert.Equal(new double[] { 1, 0, 0, 0, 0, 0 }, mock.GetAssignment("20 / D", "NX"));
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
