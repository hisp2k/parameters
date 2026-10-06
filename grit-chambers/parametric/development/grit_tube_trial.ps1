$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritTubeTrial {
 public static string Run(object o,string src,string dst){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
 d.ClearSelection2(true);bool sel=d.Extension.SelectByID2("SCREW_AXIS_30DEG_REFERENCE","SKETCH",0,0,0,false,4,null,0);
 IFeature f=d.FeatureManager.InsertProtrusionSwept4(false,false,0,false,false,0,0,true,0.005,0,0,0,false,true,true,0,false,true,0.11,0);
 if(f!=null)f.Name="SCREW_CASING_THIN_D110_T5";bool reb=d.ForceRebuild3(false);object[] bodies=(object[])((IPartDoc)d).GetBodies2(0,false);string x="";foreach(object ob in bodies){var b=(IBody2)ob;var bb=(double[])b.GetBodyBox();if(bb[3]>1.4 && bb[0]>0.1){var m=(double[])b.GetMassProperties(1);x+="vol="+m[3].ToString("G8",CultureInfo.InvariantCulture)+";faces="+b.GetFaceCount();}}bool saved=d.Save3(1,ref e,ref w);return "selected="+sel+";tube="+(f!=null)+";rebuild="+reb+";bodies="+bodies.Length+";"+x+";saved="+saved+";err="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritTubeTrial]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_CASING_TEST.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_BASE_CASING_TUBE_TEST.SLDPRT'))
