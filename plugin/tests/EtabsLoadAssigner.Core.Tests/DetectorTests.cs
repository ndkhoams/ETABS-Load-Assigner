using Xunit;

namespace EtabsLoadAssigner.Core.Tests;

/// <summary>
/// Port cua tests/test_assigner.py (phan detector) + tests/test_real_excel.py
/// (phan spot-values, chay tren fixture tong hop — file that chi dung cho
/// chuong trinh parity o /tmp, khong nam trong repo).
/// </summary>
public sealed class DetectorTests : IDisposable
{
    private readonly string _fixture;
    private readonly string _tmpDir;

    public DetectorTests()
    {
        _tmpDir = Path.Combine(Path.GetTempPath(), "ela-tests-" + Guid.NewGuid().ToString("N"));
        Directory.CreateDirectory(_tmpDir);
        _fixture = FixtureBuilder.Build(Path.Combine(_tmpDir, "longphu_bc5_synthetic.xlsx"));
    }

    public void Dispose()
    {
        try { Directory.Delete(_tmpDir, recursive: true); } catch { /* best effort */ }
    }

    [Fact]
    public void ParseCell_Range()
    {
        var lv = Detector.ParseCell("-3/+6");
        Assert.Equal(LoadValueKind.Range, lv.Kind);
        Assert.Equal(-3, lv.VMin);
        Assert.Equal(6, lv.VMax);

        var lv2 = Detector.ParseCell("67/-71");
        Assert.Equal(LoadValueKind.Range, lv2.Kind);
        Assert.Equal(67, lv2.VMin);
        Assert.Equal(-71, lv2.VMax);

        // So thu 2 khong dau "+" van la khoang (vd "-50/48" trong anh bang goc).
        var lv3 = Detector.ParseCell("-50/48");
        Assert.Equal(LoadValueKind.Range, lv3.Kind);
        Assert.Equal(-50, lv3.VMin);
        Assert.Equal(48, lv3.VMax);
    }

    [Fact]
    public void ParseCell_NumberBlankAndText()
    {
        Assert.Equal(19, Detector.ParseCell(19).Value);
        Assert.Equal(19, Detector.ParseCell("19").Value);
        Assert.Equal(-2, Detector.ParseCell("-2").Value);
        Assert.Equal(19.5, Detector.ParseCell("19,5").Value); // dau phay thap phan
        Assert.Equal(LoadValueKind.Blank, Detector.ParseCell("").Kind);
        Assert.Equal(LoadValueKind.Blank, Detector.ParseCell(null).Kind);
        Assert.Equal(LoadValueKind.Blank, Detector.ParseCell("-").Kind);
        Assert.Equal(LoadValueKind.Text, Detector.ParseCell("abc").Kind);
    }

    [Fact]
    public void ParseCell_PlusMinusPrefix_TwoValues()
    {
        // O viet "+/- 1" (bang 90/D.1 trong file that): gia tri 1 = -1, gia tri 2 = +1 (user chot 08/11).
        var lv = Detector.ParseCell("+/- 1");
        Assert.Equal(LoadValueKind.Range, lv.Kind);
        Assert.Equal(-1, lv.VMin);
        Assert.Equal(1, lv.VMax);
        Assert.Equal("+/- 1", lv.Raw); // raw goc giu lai
        Assert.Equal(LoadValueKind.Range, Detector.ParseCell("+/-1").Kind);
        Assert.Equal(-57, Detector.ParseCell("+/- 57").VMin);
        Assert.Equal(57, Detector.ParseCell("+/- 57").VMax);
        Assert.Equal(LoadValueKind.Range, Detector.ParseCell("± 1").Kind);
        Assert.Equal(-10, Detector.ParseCell("+ / -10").VMin); // ke ca khoang trang
        Assert.Equal(10, Detector.ParseCell("+ / -10").VMax);
        Assert.Equal(0, Detector.ParseCell("-/+ 0").VMin);
        Assert.Equal(0, Detector.ParseCell("-/+ 0").VMax);
    }

    [Fact]
    public void Detector_FindsPointsRowsPatterns()
    {
        var t = Detector.DetectExcel(_fixture);
        Assert.Equal(new[] { "20 / D", "20 / E", "27 / D", "27 / E" }, t.Points);
        Assert.Equal(26, t.Rows.Count);
        Assert.Equal(29, t.Patterns.Count);
        Assert.Equal(new[] { "BC1", "BC2", "BT1" }, t.Patterns.Take(3).Select(p => p.Name));
        Assert.Empty(t.Warnings);

        var dead = t.Rows.Single(r => r.Name == "Dead loads");
        Assert.Equal(-2, dead.Values["20 / D"]["Hy"].Value);
        Assert.Equal(19, dead.Values["20 / D"]["Vz"].Value);
        Assert.Equal(2, dead.Values["20 / E"]["Hy"].Value);

        var windY = t.Rows.Single(r => r.Name == "Wind +Y");
        Assert.Equal(LoadValueKind.Range, windY.Values["20 / E"]["Vz"].Kind);
        Assert.Equal(6, windY.Values["20 / E"]["Vz"].VMax);

        var imperf = t.Rows.Single(r => r.Name == "Imperfektion X");
        Assert.True(imperf.Reversible);
    }

    [Fact]
    public void Detector_DetectsMoments_WhenSixColumnsPerPoint()
    {
        // Bang co mo men (user chot 08/11 — mo rong cho tuong lai): moi diem
        // 6 cot Hx/Hy/Vz/Mx/My/Mz. Detector phai nhan ra va doc ca mo men.
        var grid = new List<List<object?>>
        {
            new() { "LONG PHU BC-5", "", "20 / D", "", "", "", "", "" },
            new() { "Foundation loads", "", "Hx", "Hy", "Vz", "Mx", "My", "Mz" },
            new() { "", "", "[kN]", "[kN]", "[kN]", "[kN·m]", "[kN·m]", "[kN·m]" },
            new() { "Dead loads", "", 0, -2, 19, 5, -3, 2 },
            new() { "Wind +Y", "", 0, 7, -11, 0, 4, -6 },
        };
        var t = Detector.DetectFromGrid(grid, "test", "Foundation loads");
        Assert.True(t.HasMoments);
        Assert.Equal(new[] { "20 / D" }, t.Points);
        Assert.Equal(2, t.Rows.Count);
        var dead = t.Rows.Single(r => r.Name == "Dead loads");
        Assert.Equal(19, dead.Values["20 / D"]["Vz"].Value);
        Assert.Equal(5, dead.Values["20 / D"]["Mx"].Value);
        Assert.Equal(-3, dead.Values["20 / D"]["My"].Value);
        Assert.Equal(2, dead.Values["20 / D"]["Mz"].Value);
        Assert.Empty(t.Warnings);
    }

    [Fact]
    public void Detector_NoMoments_WhenThreeColumnsPerPoint()
    {
        // Bang hien tai chi co luc (3 cot/diem): HasMoments = false, khong
        // co khoa Mx/My/Mz — cot mo men o grid TU AN (user chot 08/11).
        var t = Detector.DetectExcel(_fixture);
        Assert.False(t.HasMoments);
        var dead = t.Rows.Single(r => r.Name == "Dead loads");
        Assert.False(dead.Values["20 / D"].ContainsKey("Mx"));
        Assert.False(dead.Values["20 / D"].ContainsKey("My"));
        Assert.False(dead.Values["20 / D"].ContainsKey("Mz"));
    }

    [Fact]
    public void Detector_ListSheets()
    {
        var sheets = Detector.ListSheets(_fixture);
        Assert.Equal(new[] { "Foundation loads", "Load Patterns" }, sheets);
    }

    [Fact]
    public void Detector_DetectFile_RejectsUnsupportedFormats()
    {
        Assert.Throws<NotSupportedException>(() => Detector.DetectFile("x.pdf"));
        Assert.Throws<NotSupportedException>(() => Detector.DetectFile("x.xls"));
        Assert.Throws<NotSupportedException>(() => Detector.DetectFile("x.txt"));
    }

    [Fact]
    public void Detector_DetectFile_NullSheet_PicksBestSheet()
    {
        // Fallback (user chot 08/11, anh build 201251): sheet dau tien
        // (README) khong co data thi tu dong chuyen sang sheet tiep theo co
        // data — DetectFile(path, null) quet tat ca sheet va chon bang co
        // nhieu dong tai nhat. Chi khi ca file khong co data moi bao loi.
        // Fixture tong hop co nhieu sheet; sheet null phai tra ve bang co data.
        var t = Detector.DetectFile(_fixture, null);
        Assert.True(t.Rows.Count > 0);
        Assert.True(t.Points.Count > 0);
        // Sheet cu the khong co data (vd README trong file that) tra bang rong.
        var empty = Detector.DetectFile(_fixture, "KHONG_CO_SHEET_NAY");
        Assert.Empty(empty.Rows);
    }

    [Fact]
    public void ProfileSheet_RefusesEmptyTable()
    {
        // Loi truoc day (user bao 08/11, anh build 195953): tu dong luu khi
        // bang chua nhan dien xong (vd sheet README 0 dong) de ghi de sheet
        // "LoadAssigner" thanh trang (chi con header + phuong-chieu). Gio
        // WriteProfileSheet TU CHOI ghi neu bang rong — UI cung chan truoc
        // khi goi (nut Luu bao loi, khong ghi).
        string copy = Path.Combine(_tmpDir, "empty.xlsx");
        File.Copy(_fixture, copy);
        var empty = new FoundationTable { Title = "rong", Sheet = "README" };
        Assert.Throws<InvalidOperationException>(() =>
            Detector.WriteProfileSheet(copy, new Profile(), empty));
        // Sheet cu (neu co) khong bi xoa khi ghi bi tu choi.
        Assert.Null(Detector.ReadProfileSheet(copy));
    }

    [Fact]
    public void ProfileSheet_RoundTrip()
    {
        // Chua co sheet -> ReadProfileSheet tra null.
        Assert.Null(Detector.ReadProfileSheet(_fixture));
        var table = Detector.DetectFile(_fixture);
        var profile = new Profile();
        profile.PatternMap["Dead loads"] = new RowPattern { Left = "DLS", Right = "" };
        profile.PatternMap["Wind +Y"] = new RowPattern { Left = "WY+1", Right = "WY+2" };
        profile.Axis.HxAxis = "X"; profile.Axis.HxSign = +1;
        profile.Axis.HyAxis = "Y"; profile.Axis.HySign = +1;
        profile.Axis.VzAxis = "Z"; profile.Axis.VzSign = -1;
        profile.ReplaceExisting = true;
        // Ghi vao 1 ban sao (khong sua fixture goc).
        string copy = Path.Combine(_tmpDir, "copy.xlsx");
        File.Copy(_fixture, copy);
        Detector.WriteProfileSheet(copy, profile, table);
        // Doc lai: match + phuong-chieu + ghi de phai khop.
        var back = Detector.ReadProfileSheet(copy);
        Assert.NotNull(back);
        Assert.Equal("DLS", back!.PatternFor("Dead loads").Left);
        Assert.Equal("", back.PatternFor("Dead loads").Right);
        Assert.Equal("WY+1", back.PatternFor("Wind +Y").Left);
        Assert.Equal("WY+2", back.PatternFor("Wind +Y").Right);
        Assert.Equal("X", back.Axis.HxAxis);
        Assert.Equal(1, back.Axis.HxSign);
        Assert.Equal("Z", back.Axis.VzAxis);
        Assert.Equal(-1, back.Axis.VzSign);
        Assert.True(back.ReplaceExisting);
        // Ghi de lan 2 (doi match) phai cap nhat dung, khong tao sheet thua.
        profile.PatternMap["Dead loads"] = new RowPattern { Left = "DLS2", Right = "" };
        profile.ReplaceExisting = false;
        Detector.WriteProfileSheet(copy, profile, table);
        var back2 = Detector.ReadProfileSheet(copy)!;
        Assert.Equal("DLS2", back2.PatternFor("Dead loads").Left);
        Assert.False(back2.ReplaceExisting);
        Assert.Equal("WY+1", back2.PatternFor("Wind +Y").Left);
    }
}
