$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;
using SolidWorks.Interop.sldworks;
public static class GritAxis {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 public static string Run(object o,string src,string dst,double b,double l){
  ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL:"+e;
  if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  double y0=0.4,z0=0.07,y1=l+0.1,z1=z0+(y1-y0)*Math.Tan(Math.PI/6.0);
  d.ClearSelection2(true);d.SketchManager.Insert3DSketch(true);
  d.SketchManager.AddToDB=true;d.SketchManager.DisplayWhenAdded=false;
  object seg=d.SketchManager.CreateLine(b/2,y0,z0,b/2,y1,z1);
  d.SketchManager.AddToDB=false;d.SketchManager.DisplayWhenAdded=true;
  d.SketchManager.Insert3DSketch(true);
  IFeature axis=Last(d);axis.Name="SCREW_AXIS_30DEG_REFERENCE";
  bool reb=d.ForceRebuild3(false),saved=d.Save3(1,ref e,ref w);
  return "axis="+(seg!=null)+";startY="+y0+";endY="+y1+";endZ="+z1+";aboveWater="+(z1>0.55)+";rebuild="+reb+";saved="+saved+";saveErr="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritAxis]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_BASE_V5_20261003.SLDPRT'),(Join-Path $dir 'GRIT_DETAIL_BASE_V6_20261003.SLDPRT'),0.7,1.35)
[GritAxis]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_NARROW_V5_20261003.SLDPRT'),(Join-Path $dir 'GRIT_DETAIL_NARROW_V6_20261003.SLDPRT'),0.6,1.5)
[GritAxis]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_SHORT_WIDE_V5_20261003.SLDPRT'),(Join-Path $dir 'GRIT_DETAIL_SHORT_WIDE_V6_20261003.SLDPRT'),0.8,1.25)
