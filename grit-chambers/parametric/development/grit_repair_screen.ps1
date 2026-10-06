$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;
using SolidWorks.Interop.sldworks;
public static class GritScreenRepair {
 static string Last(IModelDoc2 d) {IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last==null?"":last.Name;}
 public static string Run(object o,string p,double b,int cols) {
  ISldWorks s=(ISldWorks)o; int e=0,w=0; IModelDoc2 d=(IModelDoc2)s.OpenDoc6(p,1,0,"",ref e,ref w);
  if(d==null)return "OPEN_FAIL:"+e;
  d.ClearSelection2(true); d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0); d.SketchManager.InsertSketch(true);
  d.SketchManager.CreateCornerRectangle(0.03,-0.002,0,b-0.03,-0.65,0);
  d.SketchManager.InsertSketch(true);string sk=Last(d);bool selected=d.Extension.SelectByID2(sk,"SKETCH",0,0,0,false,4,null,0);
  IFeature panel=d.FeatureManager.FeatureExtrusion2(true,false,false,0,0,0.002,0,false,false,false,false,0,0,false,false,false,false,false,true,true,3,0.250,false);
  if(panel==null)return "PANEL_FAIL;sk="+sk+";sel="+selected;
  panel.Name="DISTRIBUTOR_SOLID_PANEL";
  d.ClearSelection2(true);d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0);d.SketchManager.InsertSketch(true);
  for(int c=0;c<cols;c++){double x=0.03+(c+0.5)*(b-0.06)/cols;for(int r=0;r<15;r++){double z=0.125+r*0.0285;d.SketchManager.CreateCircleByRadius(x,-z,0,0.011);}}
  d.SketchManager.InsertSketch(true);sk=Last(d);selected=d.Extension.SelectByID2(sk,"SKETCH",0,0,0,false,4,null,0);
  IFeature cut=d.FeatureManager.FeatureCut3(true,false,false,0,0,0.004,0,false,false,false,false,0,0,false,false,false,false,false,true,true,false,false,false,3,0.249,false);
  if(cut!=null)cut.Name="DISTRIBUTOR_D22_HOLES";
  bool reb=d.ForceRebuild3(false);bool save=d.Save3(1,ref e,ref w);bool pw=false,cw=false;
  int pe=panel.GetErrorCode2(out pw),ce=cut==null?-1:cut.GetErrorCode2(out cw);
  return "panel="+pe+";cut="+ce+";cutCreated="+(cut!=null)+";sk="+sk+";selected="+selected+";rebuild="+reb+";saved="+save+";saveErr="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritScreenRepair]::Run($sw,(Join-Path $dir 'GRIT_DETAIL_NARROW_20261003.SLDPRT'),0.6,14)
