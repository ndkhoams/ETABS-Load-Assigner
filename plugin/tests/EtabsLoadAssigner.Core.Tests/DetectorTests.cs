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
}
