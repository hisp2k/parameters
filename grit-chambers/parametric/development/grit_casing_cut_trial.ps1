$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using SolidWorks.Interop.sldworks;
public static class GritCasingCut {
 public static string Run(object o,string src,string dst){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  d.ClearSelection2(true);bool sel=d.Extension.SelectByID2("SCREW_AXIS_30DEG_REFERENCE","SKETCH",0,0,0,false,4,null,0);
  IFeature f=d.FeatureManager.InsertCutSwept5(false,false,0,false,false,0,0,false,0,0,0,0,true,true,0,false,false,false,false,true,0.12,0);
  if(f!=null)f.Name="SEALED_SCREW_PASSAGE_D120";bool reb=d.ForceRebuild3(false);bool saved=d.Save3(1,ref e,ref w);bool fw=false;int fe=f==null?-1:f.GetErrorCode2(out fw);return "selected="+sel+";cut="+(f!=null)+";featureError="+fe+";rebuild="+reb+";saved="+saved+";err="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritCasingCut]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_FRAME_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_BASE_CASING_TEST.SLDPRT'))
