$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritRails {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 public static string Run(object o,string src,string dst,double b,double l){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_FAIL:"+e;
  d.ClearSelection2(true);d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0);d.SketchManager.InsertSketch(true);d.SketchManager.AddToDB=true;
  d.SketchManager.CreateCornerRectangle(0.05,0.05,0,l-0.05,0.09,0);d.SketchManager.CreateCornerRectangle(0.05,b-0.09,0,l-0.05,b-0.05,0);
  d.SketchManager.AddToDB=false;d.SketchManager.InsertSketch(true);var sk=Last(d);d.ClearSelection2(true);d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0);
  IFeature f=d.FeatureManager.FeatureExtrusion2(true,false,true,0,0,0.04,0,false,false,false,false,0,0,false,false,false,false,true,true,true,3,0.02,true);if(f!=null)f.Name="FRAME_LONGITUDINAL_RAILS";
  bool reb=d.ForceRebuild3(false);var bodies=(object[])((IPartDoc)d).GetBodies2(0,false);string boxes="";foreach(object ob in bodies){var bb=(double[])((IBody2)ob).GetBodyBox();if(bb[1]<-0.01){for(int i=0;i<6;i++)boxes+=bb[i].ToString("G5",CultureInfo.InvariantCulture)+";";boxes+="|";}}bool save=d.Save3(1,ref e,ref w);return "feature="+(f!=null)+";rebuild="+reb+";bodies="+bodies.Length+";boxes="+boxes+";saved="+save;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritRails]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_FRAME_TEST2.SLDPRT'),(Join-Path $dir 'GRIT_PILOT_BASE_FRAME_TEST3.SLDPRT'),0.7,1.35)
