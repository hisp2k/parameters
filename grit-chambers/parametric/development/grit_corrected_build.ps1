$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;
using System.Globalization;
using SolidWorks.Interop.sldworks;
public static class GritCorrectedBuild {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static bool RightSketch(IModelDoc2 d){d.ClearSelection2(true);bool ok=d.Extension.SelectByID2("Справа","PLANE",0,0,0,false,0,null,0);if(ok)d.SketchManager.InsertSketch(true);return ok;}
 static string Status(IFeature f){if(f==null)return "FAILED";bool w=false;return f.Name+"/"+f.GetErrorCode2(out w)+"/"+w;}
 static IFeature Panel(IModelDoc2 d,string name,double u0,double u1,double v0,double v1,double x,int cols){
  if(!RightSketch(d))return null;
  d.SketchManager.AddToDB=true;d.SketchManager.DisplayWhenAdded=false;
  d.SketchManager.CreateCornerRectangle(u0,v0,0,u1,v1,0);
  if(cols>0)for(int c=0;c<cols;c++){double u=u0+(c+0.5)*(u1-u0)/cols;for(int r=0;r<15;r++){double v=0.125+r*0.0285;d.SketchManager.CreateCircleByRadius(u,v,0,0.011);}}
  d.SketchManager.AddToDB=false;d.SketchManager.DisplayWhenAdded=true;d.SketchManager.InsertSketch(true);
  IFeature sk=Last(d);var seg=(object[])((ISketch)sk.GetSpecificFeature2()).GetSketchSegments();
  if(seg.Length!=4+cols*15)return null;
  d.ClearSelection2(true);if(!d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0))return null;
  IFeature f=d.FeatureManager.FeatureExtrusion2(true,false,false,0,0,0.002,0,false,false,false,false,0,0,false,false,false,false,false,true,true,3,x,false);
  if(f!=null)f.Name=name;return f;
 }
 static IFeature Inlet(IModelDoc2 d,double b){
  if(!RightSketch(d))return null;d.SketchManager.CreateCircleByRadius(b/2,0.42,0,0.05);d.SketchManager.InsertSketch(true);
  IFeature sk=Last(d);d.ClearSelection2(true);if(!d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,0,null,0))return null;
  IFeature f=d.FeatureManager.FeatureCut3(true,false,true,0,0,0.01,0.01,false,false,false,false,0,0,false,false,false,false,false,true,true,false,false,false,0,0,false);
  if(f!=null)f.Name="INLET_D100_OPENING";return f;
 }
 static IFeature Outlet(IModelDoc2 d,double b,double l){
  if(!RightSketch(d))return null;d.SketchManager.CreateCornerRectangle((b-0.60)/2,0.55,0,(b+0.60)/2,0.72,0);d.SketchManager.InsertSketch(true);
  IFeature sk=Last(d);d.ClearSelection2(true);if(!d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,0,null,0))return null;
  IFeature f=d.FeatureManager.FeatureCut3(true,false,true,0,0,0.01,0.01,false,false,false,false,0,0,false,false,false,false,false,true,true,false,false,false,3,l-0.005,false);
  if(f!=null)f.Name="OUTLET_WEIR_SLOT_W600";return f;
 }
 static void Tri(IModelDoc2 d,double u1,double v1,double u2,double v2,double u3,double v3){
  d.SketchManager.CreateLine(u1,v1,0,u2,v2,0);d.SketchManager.CreateLine(u2,v2,0,u3,v3,0);d.SketchManager.CreateLine(u3,v3,0,u1,v1,0);
 }
 static IFeature Floor(IModelDoc2 d,double b,double l){
  if(!RightSketch(d))return null;d.SketchManager.AddToDB=true;d.SketchManager.DisplayWhenAdded=false;
  Tri(d,0.002,-0.001,0.002,0.120,b/2-0.070,-0.001);Tri(d,b-0.002,-0.001,b-0.002,0.120,b/2+0.070,-0.001);
  d.SketchManager.AddToDB=false;d.SketchManager.DisplayWhenAdded=true;d.SketchManager.InsertSketch(true);
  IFeature sk=Last(d);var seg=(object[])((ISketch)sk.GetSpecificFeature2()).GetSketchSegments();if(seg.Length!=6)return null;
  d.ClearSelection2(true);if(!d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0))return null;
  IFeature f=d.FeatureManager.FeatureExtrusion2(true,false,false,0,0,l-0.525,0,false,false,false,false,0,0,false,false,false,false,true,true,true,3,0.275,false);
  if(f!=null)f.Name="SLOPED_SEDIMENT_FLOOR";return f;
 }
 static bool Axis(IModelDoc2 d,double b,double l){double x0=0.4,y0=0.07,x1=l+0.1,y1=y0+(x1-x0)*Math.Tan(Math.PI/6);d.ClearSelection2(true);d.SketchManager.Insert3DSketch(true);d.SketchManager.AddToDB=true;object seg=d.SketchManager.CreateLine(x0,y0,-b/2,x1,y1,-b/2);d.SketchManager.AddToDB=false;d.SketchManager.Insert3DSketch(true);Last(d).Name="SCREW_AXIS_30DEG_REFERENCE";return seg!=null;}
 public static string Run(object obj,string src,string dst,string cfg,double b,double l,int cols){
  ISldWorks sw=(ISldWorks)obj;int e=0,w=0;IModelDoc2 d=(IModelDoc2)sw.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return cfg+":OPEN_FAIL:"+e;
  d.ShowConfiguration2(cfg);d.ForceRebuild3(false);if(((IConfiguration)d.ConfigurationManager.ActiveConfiguration).Name!=cfg)return cfg+":CONFIG_FAIL";
  if(!d.SaveAs4(dst,0,1,ref e,ref w))return cfg+":SAVE_AS_FAIL:"+e;
  IFeature inlet=Inlet(d,b);
  IFeature impact=Panel(d,"INLET_IMPACT_BAFFLE",0.08,b-0.08,0.22,0.65,0.125,0);
  IFeature screen=Panel(d,"DISTRIBUTOR_D22",0.03,b-0.03,0.002,0.65,0.250,cols);
  IFeature outletBaffle=Panel(d,"OUTLET_SUBMERGED_BAFFLE",0.05,b-0.05,0.32,0.65,l-0.22,0);
  IFeature weir=Panel(d,"OVERFLOW_WEIR_Z550",0.005,b-0.005,0.002,0.55,l-0.06,0);
  IFeature outlet=Outlet(d,b,l);
  IFeature floor=Floor(d,b,l);
  bool axis=Axis(d,b,l);
  bool reb=d.ForceRebuild3(false);bool saved=d.Save3(1,ref e,ref w);object[] bodies=(object[])((IPartDoc)d).GetBodies2(0,false);
  string boxes="";foreach(object ob in bodies){double[] bb=(double[])((IBody2)ob).GetBodyBox();for(int i=0;i<6;i++)boxes+=bb[i].ToString("G6",CultureInfo.InvariantCulture)+";";boxes+="|";}
  return cfg+":inlet="+Status(inlet)+":impact="+Status(impact)+":screen="+Status(screen)+":outletBaffle="+Status(outletBaffle)+":weir="+Status(weir)+":outlet="+Status(outlet)+":floor="+Status(floor)+":axis="+axis+":rebuild="+reb+":saved="+saved+":saveError="+e+":bodies="+bodies.Length+":boxes="+boxes;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
$srcFile=Join-Path $dir 'GRIT_MASTER_V10_20261003.SLDPRT'
[GritCorrectedBuild]::Run($sw,$srcFile,(Join-Path $dir 'GRIT_PILOT_NARROW_20261003.SLDPRT'),'NARROW_600x1050',0.6,1.5,14)
[GritCorrectedBuild]::Run($sw,$srcFile,(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_20261003.SLDPRT'),'SHORT_WIDE_800x800',0.8,1.25,19)
