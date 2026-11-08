using Xunit;

namespace EtabsLoadAssigner.Core.Tests;

/// <summary>Port cua tests/test_assigner.py (phan assigner/mapping/profile/mock).</summary>
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

    private static Profile TestProfile()
    {
        var p = new Profile();
        p.PatternMap = new Dictionary<string, string>
        {
            ["Dead loads"] = "DLS",
            ["Live load roof (inacc.)"] = "LLR",
            ["Imperfektion X"] = "NX",
            ["Imperfektion Y"] = "NY",
            ["Wind +X"] = "WX+",
            ["Wind -X"] = "WX-",
            ["Wind +Y"] = "WY+1",
            ["Wind -Y"] = "WY-1",
            ["Earthquake X (LFP; 0,12g)"] = "EX",
            ["Earthquake Y (LFP; 0,12g)"] = "EY",
            ["Earthquake Z (LFP; 0,94g)"] = "EZ",
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
        var res = Assigner.BuildAssignments(t, "20 / D", TestProfile());
        var byPat = res.Assignments.ToDictionary(a => a.Pattern);
        // Dead: Hy=-2 -> Fy=-2, Vz=19 -> Fz=-19
        Assert.Equal(-2, byPat["DLS"].Fy);
        Assert.Equal(-19, byPat["DLS"].Fz);
        // Wind +Y: Hy=7, Vz=-11 -> Fy=7, Fz=+11
        Assert.Equal(7, byPat["WY+1"].Fy);
        Assert.Equal(11, byPat["WY+1"].Fz);
        // Wind -Y o 20/D co khoang -3/+6 -> max_abs = +6 -> Fz=-6
        Assert.Equal(-6, byPat["WY-1"].Fz);
        // Hang 0 bi bo qua, hang chua match bi skip (khong crash).
        Assert.Contains(res.Skipped, s => s.Reason == "chua match pattern");
    }

    [Fact]
    public void Assigner_ReversibleBoth_CreatesNeg()
    {
        var t = Detector.DetectExcel(_fixture);
        var p = TestProfile();
        p.ReversibleMode = "both";
        var res = Assigner.BuildAssignments(t, "20 / D", p);
        var negs = res.Assignments.Where(a => a.Negated).ToList();
        Assert.Contains(negs, a => a.Pattern == "NX_NEG" && a.Fx == 1);
    }

    [Fact]
    public void Assigner_DefaultProfile_AssignsBothDirections()
    {
        // User chot 08/11: hang ± gan CA 2 chieu — mac dinh reversible_mode = "both".
        Assert.Equal("both", new Profile().ReversibleMode);
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "20 / D", TestProfile());
        // 11 dong co luc + 5 ban _NEG dao dau (NX, NY, EX, EY, EZ).
        Assert.Equal(16, res.Assignments.Count);
        var negs = res.Assignments.Where(a => a.Negated).Select(a => a.Pattern).OrderBy(p => p).ToList();
        Assert.Equal(new[] { "EX_NEG", "EY_NEG", "EZ_NEG", "NX_NEG", "NY_NEG" }, negs);
        var byPat = res.Assignments.ToDictionary(a => a.Pattern);
        // Dao dau dung: NX = (-1,0,0) -> NX_NEG = (1,0,0); NY = (0,0,1) -> NY_NEG = (0,0,-1).
        Assert.Equal(1, byPat["NX_NEG"].Fx);
        Assert.Equal(-1, byPat["NY_NEG"].Fz);
        Assert.Contains(res.Warnings, w => w.Contains("NX_NEG"));
    }

    [Fact]
    public void Assigner_UnknownPoint_Skipped()
    {
        var t = Detector.DetectExcel(_fixture);
        var res = Assigner.BuildAssignments(t, "99 / Z", TestProfile());
        Assert.Empty(res.Assignments);
        Assert.Contains(res.Skipped, s => s.Reason == "diem");
    }

    [Fact]
    public void Profile_PatternFor_CaseInsensitive()
    {
        // Profile vi du luu key chu thuong, assigner dung ten goc — phai khop.
        var p = new Profile();
        p.PatternMap["dead loads"] = "DLS";
        Assert.Equal("DLS", p.PatternFor("Dead loads"));
        Assert.Equal("DLS", p.PatternFor("DEAD LOADS"));
        Assert.Equal("", p.PatternFor("Khong co"));
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
    public void MockAssign_Roundtrip()
    {
        var t = Detector.DetectExcel(_fixture);
        var mock = new MockEtabs();
        var p = TestProfile();
        p.ReversibleMode = "plus_only"; // mock khong co pattern _NEG — test roundtrip chi dung ban goc
        var res = Assigner.BuildAssignments(t, "20 / D", p);
        foreach (var a in res.Assignments)
            mock.AssignForce(a.EtabsJoint, a.Pattern, a.Values());
        var v = mock.GetAssignment("20 / D", "DLS");
        Assert.NotNull(v);
        Assert.Equal(new double[] { 0, -2, -19, 0, 0, 0 }, v);
        // Ghi de: gan lai chi giu 1 ban.
        mock.AssignForce("20 / D", "DLS", new double[] { 0, -2, -19, 0, 0, 0 }, replace: true);
        Assert.Single(mock.Assignments, a => a.Pattern == "DLS");
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
    public void MockAssign_AutoCreateNegPatterns_ThenAssignAll()
    {
        // Mo phong dung flow Assign() cua MainForm tren mock (giong kiem chung
        // Python tren file that: tao dung 6 _NEG roi gan du 18 tai — o day
        // fixture tong hop cho 5 _NEG / 16 tai vi TestProfile khong map T).
        var t = Detector.DetectExcel(_fixture);
        var mock = new MockEtabs();
        var p = TestProfile();
        p.CreateMissingPattern = true;
        var res = Assigner.BuildAssignments(t, "20 / D", p);
        Assert.Equal(16, res.Assignments.Count);
        var missing = res.Assignments.Select(a => a.Pattern).Distinct().OrderBy(x => x)
            .Where(x => !mock.PatternNames().Contains(x)).ToList();
        Assert.Equal(new[] { "EX_NEG", "EY_NEG", "EZ_NEG", "NX_NEG", "NY_NEG" }, missing);
        var existing = mock.ListPatterns();
        foreach (string name in missing)
            Assert.True(mock.CreatePattern(name, typeCode: PatternTypes.CreateTypeFor(name, existing)));
        Assert.Equal("Seismic", mock.ListPatterns().Single(x => x.Name == "EX_NEG").Type);
        Assert.Equal("Notional", mock.ListPatterns().Single(x => x.Name == "NX_NEG").Type);
        foreach (var a in res.Assignments)
            mock.AssignForce(a.EtabsJoint, a.Pattern, a.Values());
        Assert.Equal(16, mock.Assignments.Count);
        Assert.Equal(new double[] { 0, -2, -19, 0, 0, 0 }, mock.GetAssignment("20 / D", "DLS"));
        Assert.Equal(new double[] { 1, 0, 0, 0, 0, 0 }, mock.GetAssignment("20 / D", "NX_NEG"));
    }

    [Fact]
    public void Profile_SaveLoad_Roundtrip()
    {
        var p = TestProfile();
        p.PointAlias = new Dictionary<string, string> { ["20 / D"] = "J-20D" };
        p.Axis.VzSign = -1;
        string f = Path.Combine(_tmpDir, "prof.json");
        p.Save(f);
        var p2 = Profile.Load(f);
        Assert.Equal("DLS", p2.PatternMap["Dead loads"]);
        Assert.Equal("J-20D", p2.PointAlias["20 / D"]);
        Assert.Equal(-1, p2.Axis.VzSign);
        Assert.Equal("both", p2.ReversibleMode);
    }

    [Fact]
    public void PreviewText_ContainsAssignmentsAndTotals()
    {
        var t = Detector.DetectExcel(_fixture);
        var p = TestProfile();
        var res = Assigner.BuildAssignments(t, "20 / D", p);
        string text = Assigner.PreviewText(t, "20 / D", p, res);
        Assert.Contains("DLS", text);
        Assert.Contains("WY+1", text);
        Assert.Contains("Tong theo pattern:", text);
    }
}
