$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using SolidWorks.Interop.sldworks;
public static class GritFaceCutTrial {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static double BiggestVolume(IModelDoc2 d){object[] a=(object[])((IPartDoc)d).GetBodies2(0,false);double max=0;foreach(object o in a){double[] mp=(double[])((IBody2)o).GetMassProperties(1);if(mp[3]>max)max=mp[3];}return max;}
 public static string Run(object o,string src,string dst,double b){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";double before=BiggestVolume(d);if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  d.ClearSelection2(true);bool face=d.Extension.SelectByID2("","FACE",b/2,0,0.42,false,0,null,0);
  if(!face)return "FACE_SELECT_FAIL";
  d.SketchManager.InsertSketch(true);object circ=d.SketchManager.CreateCircleByRadius(b/2,-0.42,0,0.05);d.SketchManager.InsertSketch(true);
  IFeature sk=Last(d);d.ClearSelection2(true);bool selected=d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,0,null,0);
  IFeature cut=d.FeatureManager.FeatureCut3(true,false,false,0,0,0.008,0.008,false,false,false,false,0,0,false,false,false,false,false,true,true,false,false,false,0,0,false);
  if(cut!=null)cut.Name="INLET_D100_CUT";bool reb=d.ForceRebuild3(false);double after=BiggestVolume(d);bool saved=d.Save3(1,ref e,ref w);
  return "face="+face+";circle="+(circ!=null)+";sketch="+sk.Name+";selected="+selected+";cut="+(cut!=null)+";before="+before+";after="+after+";delta="+(before-after)+";rebuild="+reb+";saved="+saved+";error="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritFaceCutTrial]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_BASE_V6_20261003.SLDPRT'),(Join-Path $dir 'GRIT_DETAIL_BASE_V7_20261003.SLDPRT'),0.7)
