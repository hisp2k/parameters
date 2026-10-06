$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using SolidWorks.Interop.sldworks;
public static class GritFrameBuilder {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static bool Begin(IModelDoc2 d){d.ClearSelection2(true);bool q=d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0);if(q){d.SketchManager.InsertSketch(true);d.SketchManager.AddToDB=true;d.SketchManager.DisplayWhenAdded=false;}return q;}
 static IFeature End(IModelDoc2 d,string name,double depth,int t0,double off,bool rev){d.SketchManager.AddToDB=false;d.SketchManager.DisplayWhenAdded=true;d.SketchManager.InsertSketch(true);IFeature sk=Last(d);d.ClearSelection2(true);if(!d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0))return null;IFeature f=d.FeatureManager.FeatureExtrusion2(true,false,true,0,0,depth,0,false,false,false,false,0,0,false,false,false,false,true,true,true,t0,off,rev);if(f!=null)f.Name=name;return f;}
 static void Rect(IModelDoc2 d,double x0,double u0,double x1,double u1){d.SketchManager.CreateCornerRectangle(x0,u0,0,x1,u1,0);}
 static string State(IFeature f){if(f==null)return "FAILED";bool w=false;return f.Name+"/"+f.GetErrorCode2(out w)+"/"+w;}
 public static string Run(object o,string src,string dst,double b,double l){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL:"+e;if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  if(!Begin(d))return "TOP_PLANE_FAIL";double[] xs={0.05,l-0.09},us={0.05,b-0.09};foreach(double x in xs)foreach(double u in us)Rect(d,x,u,x+0.04,u+0.04);IFeature legs=End(d,"FRAME_LEGS_40X40_H500",0.5,0,0,false);
  if(!Begin(d))return "TOP_PLANE_FAIL_2";Rect(d,0.05,0.05,l-0.05,0.09);Rect(d,0.05,b-0.09,l-0.05,b-0.05);IFeature rails=End(d,"FRAME_LONGITUDINAL_RAILS",0.04,3,0.02,true);
  if(!Begin(d))return "TOP_PLANE_FAIL_3";Rect(d,0.05,0.09,0.09,b-0.09);Rect(d,l-0.09,0.09,l-0.05,b-0.09);IFeature cross=End(d,"FRAME_TRANSVERSE_RAILS",0.04,3,0.02,true);
  if(!Begin(d))return "TOP_PLANE_FAIL_4";double[] px={0.02,l-0.12},pu={0.02,b-0.12};foreach(double x in px)foreach(double u in pu)Rect(d,x,u,x+0.10,u+0.10);IFeature pads=End(d,"FRAME_FOOT_PADS_100X100",0.01,3,0.5,true);
  bool reb=d.ForceRebuild3(false);object[] bodies=(object[])((IPartDoc)d).GetBodies2(0,false);bool saved=d.Save3(1,ref e,ref w);
  return "legs="+State(legs)+";rails="+State(rails)+";cross="+State(cross)+";pads="+State(pads)+";rebuild="+reb+";bodies="+bodies.Length+";saved="+saved+";saveErr="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritFrameBuilder]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_BASE_FRAME_20261003.SLDPRT'),0.7,1.35)
[GritFrameBuilder]::Run($sw,(Join-Path $dir 'GRIT_PILOT_NARROW_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_NARROW_FRAME_20261003.SLDPRT'),0.6,1.5)
[GritFrameBuilder]::Run($sw,(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_FRAME_20261003.SLDPRT'),0.8,1.25)
