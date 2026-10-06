$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritPilotFinish {
 static string State(IFeature f){if(f==null)return "FAILED";bool w=false;return f.Name+"/"+f.GetErrorCode2(out w)+"/"+w;}
 public static string Run(object o,string src,string dst){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL:"+e;if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  d.ClearSelection2(true);bool p1=d.Extension.SelectByID2("SCREW_AXIS_30DEG_REFERENCE","SKETCH",0,0,0,false,4,null,0);
  IFeature passage=d.FeatureManager.InsertCutSwept5(false,false,0,false,false,0,0,false,0,0,0,0,true,true,0,false,false,false,false,true,0.12,0);if(passage!=null)passage.Name="SEALED_SCREW_PASSAGE_D120";
  d.ClearSelection2(true);bool p2=d.Extension.SelectByID2("SCREW_AXIS_30DEG_REFERENCE","SKETCH",0,0,0,false,4,null,0);
  IFeature tube=d.FeatureManager.InsertProtrusionSwept4(false,false,0,false,false,0,0,true,0.005,0,0,0,false,true,true,0,false,true,0.11,0);if(tube!=null)tube.Name="SCREW_CASING_ID110_T5";
  d.ClearSelection2(true);bool p3=d.Extension.SelectByID2("SCREW_AXIS_30DEG_REFERENCE","SKETCH",0,0,0,false,4,null,0);
  IFeature screw=d.FeatureManager.InsertProtrusionSwept4(false,false,0,false,false,0,0,false,0,0,0,0,false,true,true,0,false,true,0.10,0);if(screw!=null)screw.Name="SCREW_OUTER_ENVELOPE_D100";
  bool rebuilt=d.ForceRebuild3(false);object[] bodies=(object[])((IPartDoc)d).GetBodies2(0,false);bool saved=d.Save3(1,ref e,ref w);
  return "file="+d.GetTitle()+";pathSelected="+p1+"/"+p2+"/"+p3+";passage="+State(passage)+";tube="+State(tube)+";screw="+State(screw)+";rebuild="+rebuilt+";bodies="+bodies.Length+";saved="+saved+";saveErr="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritPilotFinish]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_FRAME_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_BASE_CAD_20261003.SLDPRT'))
[GritPilotFinish]::Run($sw,(Join-Path $dir 'GRIT_PILOT_NARROW_FRAME_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_NARROW_CAD_20261003.SLDPRT'))
[GritPilotFinish]::Run($sw,(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_FRAME_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT'))
