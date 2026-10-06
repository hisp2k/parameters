$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritFrameTest {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 public static string Run(object o,string src,string dst,double b,double l){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_FAIL:"+e;
  d.ClearSelection2(true);bool pl=d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0);d.SketchManager.InsertSketch(true);d.SketchManager.AddToDB=true;
  double[] xs={0.05,l-0.09},zs={0.05,b-0.09};foreach(double x in xs)foreach(double z in zs)d.SketchManager.CreateCornerRectangle(x,z,0,x+0.04,z+0.04,0);
  d.SketchManager.AddToDB=false;d.SketchManager.InsertSketch(true);var sk=Last(d);var seg=(object[])((ISketch)sk.GetSpecificFeature2()).GetSketchSegments();d.ClearSelection2(true);bool sel=d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0);
  IFeature f=d.FeatureManager.FeatureExtrusion2(true,false,true,0,0,0.5,0,false,false,false,false,0,0,false,false,false,false,false,true,true,0,0,false);if(f!=null)f.Name="FRAME_FOUR_LEGS_40X40";
  bool reb=d.ForceRebuild3(false);int n=((object[])((IPartDoc)d).GetBodies2(0,false)).Length;bool saved=d.Save3(1,ref e,ref w);return "plane="+pl+";selected="+sel+";segments="+seg.Length+";feature="+(f!=null)+";rebuild="+reb+";bodies="+n+";saved="+saved+";err="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritFrameTest]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_20261003.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_BASE_FRAME_TEST2.SLDPRT'),0.7,1.35)
