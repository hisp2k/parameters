$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritInletCutTest {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static double Volume(IModelDoc2 d){var a=(object[])((IPartDoc)d).GetBodies2(0,false);var m=(double[])((IBody2)a[0]).GetMassProperties(1);return m[3];}
 public static string Run(object o,string src,string dst){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";double before=Volume(d);if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_FAIL";
 d.ClearSelection2(true);d.Extension.SelectByID2("Справа","PLANE",0,0,0,false,0,null,0);d.SketchManager.InsertSketch(true);d.SketchManager.CreateCircleByRadius(0.35,0.42,0,0.05);d.SketchManager.InsertSketch(true);var sk=Last(d);d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,0,null,0);
 IFeature f=d.FeatureManager.FeatureCut3(true,false,false,0,0,0.01,0.01,false,false,false,false,0,0,false,false,false,false,false,true,true,false,false,false,0,0,false);if(f!=null)f.Name="INLET_D100_CUT";
 bool reb=d.ForceRebuild3(false);double after=Volume(d);bool saved=d.Save3(1,ref e,ref w);return "cut="+(f!=null)+";before="+before.ToString("G10",CultureInfo.InvariantCulture)+";after="+after.ToString("G10",CultureInfo.InvariantCulture)+";delta="+(before-after).ToString("G10",CultureInfo.InvariantCulture)+";reb="+reb+";save="+saved;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
[GritInletCutTest]::Run($sw,'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT','C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_INLET_CUT_TEST.SLDPRT')
