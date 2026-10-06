$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;
using SolidWorks.Interop.sldworks;
public class BuildGritMasterV2 {
 public static string Run(object o,string target){
  var sw=(ISldWorks)o;
  var doc=(IModelDoc2)sw.NewPart();
  if(doc==null)throw new Exception("NewPart returned null");
  string[] names={"AI_Q_Peak","AI_B_Bath","AI_L_Settle","AI_L_Inlet","AI_L_Outlet","AI_L_Bath",
   "AI_H_Water","AI_H_Freeboard","AI_H_Bath","AI_Shell_Thickness","AI_Inlet_DN","AI_Weir_Width",
   "AI_Inlet_Baffle_Offset","AI_Distributor_Open_Area","AI_Distributor_Hole_Dia","AI_Distributor_Blind_Zone",
   "AI_Outlet_Baffle_Depth","AI_Screw_Diameter","AI_Screw_Pitch","AI_Screw_Angle","AI_Screw_Rpm",
   "AI_Screw_Clearance","AI_Liner_Thickness","AI_Discharge_Height","AI_Frame_Height"};
  string[] vals={"0.006","700","900","250","200","1350","550","200","750","2","100","600",
   "125","0.28","22","110","250","100","100","30","15","5","5","650","500"};
  var eq=(IEquationMgr)doc.GetEquationMgr(); string failed="";
  for(int i=0;i<names.Length;i++){
   int index=eq.Add2(eq.GetCount(),"\""+names[i]+"\" = "+vals[i],true);
   if(index<0)failed+=names[i]+",";
  }
  int errors=0,warnings=0;
  bool saved=doc.Extension.SaveAs(target,0,1,null,ref errors,ref warnings);
  return "COUNT="+eq.GetCount()+";FAILED="+failed+";SAVED="+saved+";ERR="+errors+";WARN="+warnings;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
[BuildGritMasterV2]::Run($sw,'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V2_20261003.SLDPRT')
