using CSiAPIv1;

namespace EtabsLoadAssigner.Plugin;

/// <summary>
/// Plugin ETABS — class BAT BUOC phai ten "cPlugin" (ETABS tim class nay khi nap DLL).
/// Nap: ETABS > Tools > Add/Show Plug-Ins... > Browse toi EtabsLoadAssignerPlugin.dll > Add.
/// Xong no hien thanh 1 dong trong menu Tools; bam la chay ngay tren model dang mo.
///
/// Hop dong CSI (verified tu CSiAPIv1.dll that, ETABS v22 cua user):
///   - cPluginContract.Main(ref cSapModel SapModel, ref cPluginCallback ISapPlugin)
///   - cPluginContract.Info(ref string Text) -> 0 neu OK (text hien khi add plugin lan dau)
///   - cPluginCallback.Finish(0) phai goi ngay truoc khi plugin dong.
///   - Doi tuong cPlugin bi huy giua cac lan goi tu menu Tools, nen moi cai dat
///     phai luu ra file (profile JSON o %AppData%\EtabsLoadAssigner) — xem MainForm.
/// </summary>
public sealed class cPlugin : cPluginContract
{
    public int Info(ref string Text)
    {
        Text = "ETABS Load Assigner — gan tai mong tu file Excel (LONG PHU BC-5) vao ETABS.\n" +
               "Mo file Excel bang tai mong, chon diem, map phuong/chieu va pattern, " +
               "roi gan tai diem (PointObj.SetLoadForce) vao model dang mo.\n" +
               "Yeu cau: ETABS v22 tro len (.NET 8 + CSiAPIv1).";
        return 0;
    }

    public void Main(ref cSapModel sapModel, ref cPluginCallback pluginCallback)
    {
        try
        {
            // Khong goi ApplicationConfiguration.Initialize() / EnableVisualStyles() o day:
            // plugin chay trong tien trinh ETABS, khong duoc doi setting WinForms cua host.
            var api = new RealEtabs(sapModel);
            using var form = new MainForm(api);
            form.ShowDialog();
        }
        finally
        {
            // BAT BUOC: bao ETABS la plugin da xong (ke ca khi form loi).
            pluginCallback.Finish(0);
        }
    }
}
