$ErrorActionPreference = 'Stop'
$dll = 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src = @'
using System;
using SolidWorks.Interop.sldworks;

public static class GritDetailBuilder {
  public static int LastScreenSegments=0;
  static IFeature LastFeature(IModelDoc2 d) {
    IFeature f=(IFeature)d.FirstFeature(), last=null;
    while(f!=null) {last=f; f=(IFeature)f.GetNextFeature();}
    return last;
  }
  static string LastSketchName(IModelDoc2 d) {
    IFeature last=LastFeature(d);
    return last==null ? "" : last.Name;
  }
  static IFeature Panel(IModelDoc2 d,string name,double xmin,double xmax,double zmin,double zmax,double y,bool perforated,int cols) {
    d.ClearSelection2(true);
    if(!d.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0)) return null;
    d.SketchManager.InsertSketch(true);
    d.SketchManager.CreateCornerRectangle(xmin,-zmin,0,xmax,-zmax,0);
    if(perforated) {
      d.SketchManager.AddToDB=true;
      d.SketchManager.DisplayWhenAdded=false;
      for(int c=0;c<cols;c++) {
        double x=xmin+(c+0.5)*(xmax-xmin)/cols;
        for(int r=0;r<15;r++) {
          double z=0.125+r*0.0285;
          d.SketchManager.CreateCircleByRadius(x,-z,0,0.011);
        }
      }
      d.SketchManager.AddToDB=false;
      d.SketchManager.DisplayWhenAdded=true;
    }
    d.SketchManager.InsertSketch(true);
    if(perforated) {
      ISketch sk=(ISketch)LastFeature(d).GetSpecificFeature2();
      object[] segments=(object[])sk.GetSketchSegments();
      LastScreenSegments=segments.Length;
      if(segments.Length!=4+cols*15) return null;
    }
    string sketch=LastSketchName(d);
    if(!d.Extension.SelectByID2(sketch,"SKETCH",0,0,0,false,4,null,0)) return null;
    IFeature feat=d.FeatureManager.FeatureExtrusion2(true,false,false,0,0,0.002,0,false,false,false,false,0,0,false,false,false,false,false,true,true,3,y,false);
    if(feat!=null) feat.Name=name;
    return feat;
  }
  static string FeatureState(IFeature f) {
    if(f==null) return "CREATE_FAILED";
    bool w=false; int e=f.GetErrorCode2(out w);
    return f.Name+":error="+e+":warning="+w;
  }
  public static string Run(object obj,string src,string dst,string cfg,double b,double l,int cols) {
    ISldWorks sw=(ISldWorks)obj; int e=0,w=0;
    IModelDoc2 d=(IModelDoc2)sw.OpenDoc6(src,1,0,"",ref e,ref w);
    if(d==null) return cfg+":OPEN_FAILED:"+e+":"+w;
    d.ShowConfiguration2(cfg);
    string active=((IConfiguration)d.ConfigurationManager.ActiveConfiguration).Name;
    if(active!=cfg) return cfg+":CONFIG_FAILED:"+active;
    int se=0,swarn=0;
    if(!d.SaveAs4(dst,0,1,ref se,ref swarn)) return cfg+":SAVE_AS_FAILED:"+se+":"+swarn;
    IFeature inlet=Panel(d,"INLET_IMPACT_BAFFLE",0.08,b-0.08,0.22,0.65,0.125,false,0);
    IFeature screen=Panel(d,"DISTRIBUTOR_D22",0.03,b-0.03,0.002,0.65,0.250,true,cols);
    IFeature outlet=Panel(d,"OUTLET_SUBMERGED_BAFFLE",0.05,b-0.05,0.32,0.65,l-0.22,false,0);
    IFeature weir=Panel(d,"OVERFLOW_WEIR_Z550",0.005,b-0.005,0.002,0.55,l-0.06,false,0);
    bool reb=d.ForceRebuild3(false);
    bool saved=d.Save3(1,ref se,ref swarn);
    object bodies=((IPartDoc)d).GetBodies2(0,false);
    int n=(bodies as object[])==null ? -1 : ((object[])bodies).Length;
    return cfg+":rebuild="+reb+":saved="+saved+":saveError="+se+":bodies="+n+":screenSketchSegments="+LastScreenSegments+":targetHoles="+(cols*15)+":"+FeatureState(inlet)+":"+FeatureState(screen)+":"+FeatureState(outlet)+":"+FeatureState(weir);
  }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw = New-Object -ComObject SldWorks.Application
$srcFile = 'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT'
$outDir = 'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritDetailBuilder]::Run($sw,$srcFile,(Join-Path $outDir 'GRIT_DETAIL_NARROW_V2_20261003.SLDPRT'),'NARROW_600x1050',0.600,1.500,14)
[GritDetailBuilder]::Run($sw,$srcFile,(Join-Path $outDir 'GRIT_DETAIL_SHORT_WIDE_V2_20261003.SLDPRT'),'SHORT_WIDE_800x800',0.800,1.250,19)
