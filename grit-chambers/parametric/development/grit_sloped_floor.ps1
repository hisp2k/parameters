$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;
using SolidWorks.Interop.sldworks;
public static class GritSlope {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static void Tri(IModelDoc2 d,double x1,double z1,double x2,double z2,double x3,double z3){
  d.SketchManager.CreateLine(x1,-z1,0,x2,-z2,0);
  d.SketchManager.CreateLine(x2,-z2,0,x3,-z3,0);
  d.SketchManager.CreateLine(x3,-z3,0,x1,-z1,0);
 }
 public static string Run(object o,string src,string dst,double b,double l){
  ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL:"+e;
  if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  d.ClearSelection2(true);if(!d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0))return "PLANE_FAIL";
  d.SketchManager.InsertSketch(true);d.SketchManager.AddToDB=true;d.SketchManager.DisplayWhenAdded=false;
  Tri(d,0.002,-0.001,0.002,0.120,b/2-0.070,-0.001);
  Tri(d,b-0.002,-0.001,b-0.002,0.120,b/2+0.070,-0.001);
  d.SketchManager.AddToDB=false;d.SketchManager.DisplayWhenAdded=true;d.SketchManager.InsertSketch(true);
  IFeature sk=Last(d);var seg=(object[])((ISketch)sk.GetSpecificFeature2()).GetSketchSegments();
  d.ClearSelection2(true);bool selected=d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0);
  IFeature f=d.FeatureManager.FeatureExtrusion2(true,false,false,0,0,l-0.55,0,false,false,false,false,0,0,false,false,false,false,true,true,true,3,0.275,false);
  if(f==null)return "EXTRUDE_FAIL;segments="+seg.Length+";selected="+selected;
  f.Name="SLOPED_SEDIMENT_FLOOR";bool reb=d.ForceRebuild3(false);bool fw=false;int fe=f.GetErrorCode2(out fw);bool save=d.Save3(1,ref e,ref w);
  object[] bodies=(object[])((IPartDoc)d).GetBodies2(0,false);
  return "segments="+seg.Length+";selected="+selected+";rebuild="+reb+";featureError="+fe+";featureWarning="+fw+";bodyCount="+bodies.Length+";saved="+save+";saveError="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritSlope]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_NARROW_V2_20261003.SLDPRT'),(Join-Path $dir 'GRIT_DETAIL_NARROW_V5_20261003.SLDPRT'),0.6,1.5)
[GritSlope]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_SHORT_WIDE_V2_20261003.SLDPRT'),(Join-Path $dir 'GRIT_DETAIL_SHORT_WIDE_V5_20261003.SLDPRT'),0.8,1.25)
