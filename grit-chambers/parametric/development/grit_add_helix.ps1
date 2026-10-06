$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using SolidWorks.Interop.sldworks;
public static class GritAddHelix {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 static IFeature Find(IModelDoc2 d,string name){IFeature f=(IFeature)d.FirstFeature();while(f!=null){if(f.Name==name)return f;f=(IFeature)f.GetNextFeature();}return null;}
 public static string Run(object o,string p,double b,double l){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(p,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL:"+e;
  if(Find(d,"SHAFTLESS_ROUND_COIL_D100_P100")!=null)return d.GetTitle()+":ALREADY_PRESENT";
  double length=(l+0.1-0.4)/Math.Cos(Math.PI/6),pitch=0.1,radius=0.035;int n=(int)Math.Ceiling(length/pitch*16)+1;double[] pts=new double[3*n];
  for(int i=0;i<n;i++){double a=length*i/(n-1),theta=2*Math.PI*a/pitch,ca=Math.Cos(theta),sa=Math.Sin(theta);pts[3*i]=0.4+a*Math.Cos(Math.PI/6)-radius*Math.Sin(Math.PI/6)*ca;pts[3*i+1]=0.07+a*Math.Sin(Math.PI/6)+radius*Math.Cos(Math.PI/6)*ca;pts[3*i+2]=-b/2+radius*sa;}
  d.ClearSelection2(true);d.SketchManager.Insert3DSketch(true);d.SketchManager.AddToDB=true;d.SketchManager.DisplayWhenAdded=false;
  object spline=d.SketchManager.CreateSpline2(pts,true);d.SketchManager.AddToDB=false;d.SketchManager.DisplayWhenAdded=true;d.SketchManager.Insert3DSketch(true);
  IFeature path=Last(d);path.Name="SHAFTLESS_HELIX_PATH_P100";d.ClearSelection2(true);bool sel=d.Extension.SelectByID2(path.Name,"SKETCH",0,0,0,false,4,null,0);
  IFeature coil=d.FeatureManager.InsertProtrusionSwept4(false,false,0,false,false,0,0,false,0,0,0,0,false,true,true,0,false,true,0.03,0);if(coil!=null)coil.Name="SHAFTLESS_ROUND_COIL_D100_P100";
  IFeature envelope=Find(d,"SCREW_OUTER_ENVELOPE_D100");bool suppressed=envelope!=null&&envelope.SetSuppression2(0,1,null);
  bool reb=d.ForceRebuild3(false);bool fw=false;int fe=coil==null?-1:coil.GetErrorCode2(out fw);int bodies=((object[])((IPartDoc)d).GetBodies2(0,false)).Length;bool saved=d.Save3(1,ref e,ref w);
  return d.GetTitle()+":points="+n+":spline="+(spline!=null)+":selected="+sel+":coil="+(coil!=null)+":featureError="+fe+":warning="+fw+":envelopeSuppressed="+suppressed+":rebuild="+reb+":bodies="+bodies+":saved="+saved+":saveError="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritAddHelix]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_CAD_20261003.SLDPRT'),0.7,1.35)
[GritAddHelix]::Run($sw,(Join-Path $dir 'GRIT_PILOT_NARROW_CAD_20261003.SLDPRT'),0.6,1.5)
[GritAddHelix]::Run($sw,(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT'),0.8,1.25)
