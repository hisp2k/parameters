$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritHelixTrial {
 static IFeature Last(IModelDoc2 d){IFeature f=(IFeature)d.FirstFeature(),last=null;while(f!=null){last=f;f=(IFeature)f.GetNextFeature();}return last;}
 public static string Run(object o,string src,string dst,double b,double l){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(src,1,0,"",ref e,ref w);if(d==null)return "OPEN_FAIL";if(!d.SaveAs4(dst,0,1,ref e,ref w))return "SAVE_AS_FAIL:"+e;
  double dx=l+0.1-0.4,axisLen=dx/Math.Cos(Math.PI/6),pitch=0.1,radius=0.035;int n=(int)Math.Ceiling(axisLen/pitch*16)+1;double[] pts=new double[3*n];
  for(int i=0;i<n;i++){double ax=axisLen*i/(n-1),theta=2*Math.PI*ax/pitch;double ca=Math.Cos(theta),sa=Math.Sin(theta);pts[i*3]=0.4+ax*Math.Cos(Math.PI/6)-radius*Math.Sin(Math.PI/6)*ca;pts[i*3+1]=0.07+ax*Math.Sin(Math.PI/6)+radius*Math.Cos(Math.PI/6)*ca;pts[i*3+2]=-b/2+radius*sa;}
  d.ClearSelection2(true);d.SketchManager.Insert3DSketch(true);d.SketchManager.AddToDB=true;d.SketchManager.DisplayWhenAdded=false;
  object seg=d.SketchManager.CreateSpline2(pts,true);
  d.SketchManager.AddToDB=false;d.SketchManager.DisplayWhenAdded=true;d.SketchManager.Insert3DSketch(true);
  IFeature path=Last(d);path.Name="SHAFTLESS_HELIX_PATH_P100";d.ClearSelection2(true);bool sel=d.Extension.SelectByID2(path.Name,"SKETCH",0,0,0,false,4,null,0);
  IFeature coil=d.FeatureManager.InsertProtrusionSwept4(false,false,0,false,false,0,0,false,0,0,0,0,false,true,true,0,false,true,0.03,0);if(coil!=null)coil.Name="SHAFTLESS_ROUND_COIL_D100_P100";
  bool reb=d.ForceRebuild3(false);bool warn=false;int fe=coil==null?-1:coil.GetErrorCode2(out warn);int bodies=((object[])((IPartDoc)d).GetBodies2(0,false)).Length;bool saved=d.Save3(1,ref e,ref w);
  return "points="+n+";path="+(seg!=null)+";selected="+sel+";coil="+(coil!=null)+";featureError="+fe+";warning="+warn+";rebuild="+reb+";bodies="+bodies+";saved="+saved+";saveErr="+e;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritHelixTrial]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_CAD_20261003.SLDPRT'),(Join-Path $dir 'GRIT_HELIX_TEST.SLDPRT'),0.7,1.35)
