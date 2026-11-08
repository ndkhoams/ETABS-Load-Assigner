using ETABSv1;
using System;
using System.Windows.Forms;

namespace EtabsLoadAssigner.Plugin;

/// <summary>
/// Plugin ETABS — class BAT BUOC phai ten "cPlugin" (ETABS tim class nay khi nap DLL).
/// Nap: ETABS > Tools > Add/Show Plug-Ins... > Browse toi EtabsLoadAssignerPlugin.dll > Add.
/// Xong no hien thanh 1 dong trong menu Tools; bam la chay ngay tren model dang mo.
///
/// Viet theo dung mau Ultimate Tools (repo Etabs_Plugin, .NET Framework 4.8 +
/// ETABSv1.dll — da chung minh nap duoc tren ETABS v22):
///   - KHONG implement cPluginContract, KHONG co Info() — chi co Main().
///   - Main() mo form chinh (ShowDialog) roi goi pluginCallback.Finish(0);
///     loi thi hien MessageBox + Finish(1).
///   - Doi tuong cPlugin bi huy giua cac lan goi tu menu Tools, nen moi cai dat
///     phai luu ra file (profile JSON o %AppData%\EtabsLoadAssigner) — xem MainForm.
///
/// LUU Y: ban .NET 8 + CSiAPIv1 truoc day (co Info + cPluginContract) bi ETABS
/// bao "Not Found" khi Add du duong dan/file/mo phong nap deu dung — bo han.
/// </summary>
public class cPlugin
{
    public void Main(ref cSapModel sapModel, ref cPluginCallback pluginCallback)
    {
        try
        {
            Application.EnableVisualStyles();
            var api = new RealEtabs(sapModel);
            using var form = new MainForm(api);
            form.ShowDialog();
            pluginCallback.Finish(0);
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "ETABS Load Assigner", MessageBoxButtons.OK, MessageBoxIcon.Error);
            pluginCallback.Finish(1);
        }
    }
}
