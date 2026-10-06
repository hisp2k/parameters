$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritOrientationTest {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 public static string Run(object o,string src,string dst){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_FAIL";
  d.ClearSelection2(true);bool sel=d.Extension.SelectByID2("Справа","PLANE",0,0,0,false,0,null,0);d.SketchManager.InsertSketch(true);d.SketchManager.CreateCornerRectangle(0.05,0.10,0,0.65,0.55,0);d.SketchManager.InsertSketch(true);
  var sk=Last(d);d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0);var f=d.FeatureManager.FeatureExtrusion2(true,false,false,0,0,0.002,0,false,false,false,false,0,0,false,false,false,false,false,true,true,3,0.25,false);if(f==null)return "FEATURE_FAIL;plane="+sel;
  f.Name="ORIENTATION_TEST";d.ForceRebuild3(false);d.Save3(1,ref e,ref w);var a=(object[])((IPartDoc)d).GetBodies2(0,false);string x="";foreach(object ob in a){foreach(double v in (double[])((IBody2)ob).GetBodyBox())x+=v.ToString("G6",CultureInfo.InvariantCulture)+";";x+="|";}return x;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
[GritOrientationTest]::Run($sw,'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT','C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_ORIENTATION_TEST.SLDPRT')
