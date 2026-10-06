$ErrorActionPreference = 'Stop'
$dll = 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src = @'
using System;
using SolidWorks.Interop.sldworks;
public class BuildGritMaster {
  public static string Run(object instance, string path) {
    var sw = (ISldWorks)instance;
    int errors = 0, warnings = 0;
    var doc = (IModelDoc2)sw.OpenDoc6(path, 1, 0, "", ref errors, ref warnings);
    if (doc == null) throw new Exception("OpenDoc6 failed: " + errors);
    sw.ActivateDoc2(doc.GetTitle(), true, ref errors);
    var eq = (IEquationMgr)doc.GetEquationMgr();
    string[] names = {"AI_Q_Peak","AI_B_Bath","AI_L_Settle","AI_L_Inlet","AI_L_Outlet","AI_L_Bath",
      "AI_H_Water","AI_H_Freeboard","AI_H_Bath","AI_Shell_Thickness","AI_Inlet_DN","AI_Weir_Width",
      "AI_Inlet_Baffle_Offset","AI_Distributor_Open_Area","AI_Distributor_Hole_Dia",
      "AI_Distributor_Blind_Zone","AI_Outlet_Baffle_Depth","AI_Screw_Diameter","AI_Screw_Pitch",
      "AI_Screw_Angle","AI_Screw_Rpm","AI_Screw_Clearance","AI_Liner_Thickness",
      "AI_Discharge_Height","AI_Frame_Height"};
    string[] values = {"0.006","700","900","250","200","1350","550","200","750","2","100","600",
      "125","0.28","22","110","250","100","100","30","15","5","5","650","500"};
    string log = "";
    for (int k=0;k<names.Length;k++) {
      bool found = false;
      for (int i = 0; i < eq.GetCount(); i++) if (eq.Equation[i].StartsWith("\"" + names[k] + "\"")) found = true;
      if (found) continue;
      int index = eq.Add2(eq.GetCount(), "\"" + names[k] + "\" = " + values[k], true);
      if (index < 0) log += "FAILED " + names[k] + ";";
    }
    var active = (IConfiguration)doc.ConfigurationManager.ActiveConfiguration;
    if (active.Name == "По умолчанию" || active.Name == "Default") active.Name = "BASE_700x900";
    if (doc.GetConfigurationByName("NARROW_600x1050") == null) doc.AddConfiguration3("NARROW_600x1050", "B=600 mm L=1050 mm", "", 0);
    if (doc.GetConfigurationByName("SHORT_WIDE_800x800") == null) doc.AddConfiguration3("SHORT_WIDE_800x800", "B=800 mm L=800 mm", "", 0);
    int bIndex=-1, lIndex=-1;
    for (int i=0;i<eq.GetCount();i++) {
      if (eq.Equation[i].StartsWith("\"AI_B_Bath\"")) bIndex=i;
      if (eq.Equation[i].StartsWith("\"AI_L_Settle\"")) lIndex=i;
    }
    int bN=eq.SetEquationAndConfigurationOption(bIndex,"\"AI_B_Bath\" = 600",3,new string[]{"NARROW_600x1050"});
    int lN=eq.SetEquationAndConfigurationOption(lIndex,"\"AI_L_Settle\" = 1050",3,new string[]{"NARROW_600x1050"});
    int bS=eq.SetEquationAndConfigurationOption(bIndex,"\"AI_B_Bath\" = 800",3,new string[]{"SHORT_WIDE_800x800"});
    int lS=eq.SetEquationAndConfigurationOption(lIndex,"\"AI_L_Settle\" = 800",3,new string[]{"SHORT_WIDE_800x800"});
    doc.ShowConfiguration2("BASE_700x900");
    bool rebuilt=doc.ForceRebuild3(false);
    bool saved=doc.SaveAs(path);
    return "EQUATIONS="+eq.GetCount()+";CONFIGS="+String.Join(",",(object[])doc.GetConfigurationNames())+
           ";SET_CONFIGS="+bN+","+lN+","+bS+","+lS+";REBUILD="+rebuilt+";SAVED="+saved+";"+log;
  }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw = New-Object -ComObject SldWorks.Application
[BuildGritMaster]::Run($sw, 'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\01_CAD\GRIT_MASTER_20261003.SLDPRT')
