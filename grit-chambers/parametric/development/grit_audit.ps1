$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritAudit {
 public static string Run(object o,string p,string cfg){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(p,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL:"+p+":"+e;
  d.ShowConfiguration2(cfg);bool rebuilt=d.ForceRebuild3(false);int err=0,warn=0,features=0,sketchSegments=-1;
  IFeature f=(IFeature)d.FirstFeature();while(f!=null){bool fw=false;int fe=f.GetErrorCode2(out fw);if(fe!=0)err++;if(fw)warn++;features++;
   if(f.Name=="DISTRIBUTOR_D22"){IFeature sub=(IFeature)f.GetFirstSubFeature();while(sub!=null){if(sub.GetTypeName2()=="ProfileFeature"){var sk=(ISketch)sub.GetSpecificFeature2();var arr=(object[])sk.GetSketchSegments();sketchSegments=arr.Length;}sub=(IFeature)sub.GetNextSubFeature();}}
   f=(IFeature)f.GetNextFeature();}
  object[] bodies=(object[])((IPartDoc)d).GetBodies2(0,false);bool saved=d.Save3(1,ref e,ref w);
  return "file="+d.GetTitle()+";active="+((IConfiguration)d.ConfigurationManager.ActiveConfiguration).Name+";rebuild="+rebuilt+";featureCount="+features+";featureErrors="+err+";featureWarnings="+warn+";bodies="+bodies.Length+";screenSegments="+sketchSegments+";saved="+saved+";saveErr="+e+";saveWarn="+w;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritAudit]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_CAD_20261003.SLDPRT'),'BASE_700x900')
[GritAudit]::Run($sw,(Join-Path $dir 'GRIT_PILOT_NARROW_CAD_20261003.SLDPRT'),'NARROW_600x1050')
[GritAudit]::Run($sw,(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT'),'SHORT_WIDE_800x800')
