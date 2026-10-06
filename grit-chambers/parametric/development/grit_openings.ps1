$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;
using SolidWorks.Interop.sldworks;
public static class GritOpenings {
 static IFeature Last(IModelDoc2 d) {IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static IFeature Cut(IModelDoc2 d,string name,double start,double depth) {
  d.SketchManager.InsertSketch(true);
  IFeature sketch=Last(d);
  d.ClearSelection2(true);
  if(!d.Extension.SelectByID2(sketch.Name,"SKETCH",0,0,0,false,0,null,0))return null;
  IFeature cut=d.FeatureManager.FeatureCut3(true,false,false,0,0,depth,depth,false,false,false,false,0,0,false,false,false,false,false,true,true,false,false,false,3,start,false);
  if(cut!=null)cut.Name=name;
  return cut;
 }
 public static string Run(object o,string src,string dst,double b,double l) {
  ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);
  if(d==null)return "OPEN_FAIL:"+e;
  if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  d.ClearSelection2(true);d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0);d.SketchManager.InsertSketch(true);
  d.SketchManager.CreateCircleByRadius(b/2,-0.42,0,0.05);
  IFeature inlet=Cut(d,"INLET_D100_OPENING",0,0.008);
  d.ClearSelection2(true);d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0);d.SketchManager.InsertSketch(true);
  d.SketchManager.CreateCornerRectangle((b-0.60)/2,-0.55,0,(b+0.60)/2,-0.72,0);
  IFeature outlet=Cut(d,"OUTLET_WEIR_SLOT_W600",l-0.005,0.010);
  bool rebuild=d.ForceRebuild3(false);bool save=d.Save3(1,ref e,ref w);
  return "inlet="+(inlet!=null)+";outlet="+(outlet!=null)+";rebuild="+rebuild+";saved="+save+";err="+e+";warn="+w;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritOpenings]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_BASE_V2_20261003.SLDPRT'),(Join-Path $dir 'GRIT_DETAIL_BASE_V3_20261003.SLDPRT'),0.7,1.35)
