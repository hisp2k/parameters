$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;
using SolidWorks.Interop.sldworks;
public static class GritCfdLidsTest {
 public static string Diag="";
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static IFeature Lid(IModelDoc2 d,string name,double b,double x,bool inlet){
  d.ClearSelection2(true);
  bool plane=d.Extension.SelectByID2("\u0421\u043f\u0440\u0430\u0432\u0430","PLANE",0,0,0,false,0,null,0);Diag+=name+":plane="+plane+";";if(!plane)return null;
  d.SketchManager.InsertSketch(true);
  d.SketchManager.AddToDB=true;
  if(inlet)d.SketchManager.CreateCircleByRadius(b/2,0.42,0,0.05);
  else d.SketchManager.CreateCornerRectangle((b-0.60)/2,0.55,0,(b+0.60)/2,0.72,0);
  d.SketchManager.AddToDB=false;
  d.SketchManager.InsertSketch(true);
  IFeature sk=Last(d);Diag+="sk="+sk.Name+"/"+sk.GetTypeName2()+";"; d.ClearSelection2(true);
  bool sel=d.Extension.SelectByID2(sk.Name,"SKETCH",0,0,0,false,4,null,0);Diag+="sel="+sel+";";if(!sel)return null;
  IFeature f=d.FeatureManager.FeatureExtrusion2(true,false,false,0,0,0.002,0,false,false,false,false,0,0,false,false,false,false,false,true,true,3,x,false);
  Diag+="extr="+(f!=null)+";";if(f!=null)f.Name=name;
  return f;
 }
 public static string Run(object obj,string path,string dst,double b,double l){
  Diag="";
  ISldWorks s=(ISldWorks)obj; IModelDoc2 old=(IModelDoc2)s.ActiveDoc;string oldTitle=old==null?null:old.GetTitle();
  try{
   int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(path,1,1,"",ref e,ref w);
   if(d==null)return "OPEN_FAIL:"+e;
   if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVEAS_FAIL:"+e;
   s.ActivateDoc(d.GetTitle());Diag+="target="+d.GetTitle()+";active="+((IModelDoc2)s.ActiveDoc).GetTitle()+";";
   IFeature fi=Lid(d,"CFD_INLET_LID_D100",b,0.001,true);
   IFeature fo=Lid(d,"CFD_OUTLET_LID_W600",b,l-0.001,false);
   bool rb=d.ForceRebuild3(false);object[] bodies=(object[])((IPartDoc)d).GetBodies2(0,false);
   bool wi=false,wo=false;int ei=fi==null?-1:fi.GetErrorCode2(out wi),eo=fo==null?-1:fo.GetErrorCode2(out wo);
   bool saved=d.Save3(1,ref e,ref w);
   return Diag+"inlet="+(fi!=null)+"/"+ei+"/"+wi+";outlet="+(fo!=null)+"/"+eo+"/"+wo+";rebuild="+rb+";bodies="+bodies.Length+";saved="+saved+"/"+e;
  }finally{if(oldTitle!=null)s.ActivateDoc(oldTitle);}
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$root='C:\Users\adm\Documents\Codex\2026-10-03\new-chat'
$out=Join-Path $root 'outputs\grit_chamber\02_CFD'
New-Item -ItemType Directory -Path $out -Force | Out-Null
[GritCfdLidsTest]::Run($sw,(Join-Path $root 'outputs\grit_chamber\01_CAD\GRIT_PILOT_BASE_CAD_20261003.SLDPRT'),(Join-Path $out 'GRIT_CFD_BASE_PREP_20261004.SLDPRT'),0.7,1.35)
[GritCfdLidsTest]::Run($sw,(Join-Path $root 'outputs\grit_chamber\01_CAD\GRIT_PILOT_NARROW_CAD_20261003.SLDPRT'),(Join-Path $out 'GRIT_CFD_NARROW_PREP_20261004.SLDPRT'),0.6,1.5)
[GritCfdLidsTest]::Run($sw,(Join-Path $root 'outputs\grit_chamber\01_CAD\GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT'),(Join-Path $out 'GRIT_CFD_SHORT_WIDE_PREP_20261004.SLDPRT'),0.8,1.25)
