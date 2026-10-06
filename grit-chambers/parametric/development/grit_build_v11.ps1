$ErrorActionPreference = 'Stop'
$dll = 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src = @'
using System;
using SolidWorks.Interop.sldworks;

public static class GritBuildV11 {
  public static string Run(object obj, string oldPath, string newPath) {
    ISldWorks sw = (ISldWorks)obj;
    int err=0, warn=0;
    IModelDoc2 doc=(IModelDoc2)sw.OpenDoc6(oldPath,1,0,"",ref err,ref warn);
    if(doc==null) return "OPEN_FAIL:"+err+":"+warn;
    doc.ShowConfiguration2("BASE_700x900");
    int saveErr=0,saveWarn=0;
    bool copied=doc.SaveAs4(newPath,0,1,ref saveErr,ref saveWarn);
    if(!copied) return "SAVE_AS_FAIL:"+saveErr+":"+saveWarn;
    doc.ClearSelection2(true);
    bool sel=doc.Extension.SelectByID2("Сверху","PLANE",0,0,0,false,0,null,0);
    if(!sel) return "TOP_PLANE_SELECT_FAIL";
    doc.SketchManager.InsertSketch(true);
    object lines=doc.SketchManager.CreateCornerRectangle(0.050,0.250,0,0.650,0.252,0);
    doc.SketchManager.InsertSketch(true);
    bool sketchSelected=doc.Extension.SelectByID2("Эскиз1","SKETCH",0,0,0,false,4,null,0);
    IFeature f=doc.FeatureManager.FeatureExtrusion2(true,false,false,0,0,0.45,0,false,false,false,false,0,0,false,false,false,false,false,true,true,3,0.10,false);
    if(f==null) return "EXTRUDE_FAIL;sketch="+(lines!=null)+"; sketchSelected="+sketchSelected;
    f.Name="DISTRIBUTOR_PANEL_TEST";
    bool reb=doc.ForceRebuild3(false);
    bool fw=false; int fe=f.GetErrorCode2(out fw);
    object bodies=((IPartDoc)doc).GetBodies2(0,false); string bbox="none";
    if(bodies is object[] a) {bbox="count="+a.Length; foreach(object ob in a){double[] bb=(double[])((IBody2)ob).GetBodyBox(); bbox+="|"+String.Join(",",bb);}}
    bool saved=doc.Save3(1,ref saveErr,ref saveWarn);
    return "copied="+copied+"; selected="+sel+"; feature="+f.Name+"; rebuild="+reb+"; featureError="+fe+"; featureWarning="+fw+"; bodies="+bbox+"; saved="+saved+"; saveErr="+saveErr+"; saveWarn="+saveWarn;
  }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw = New-Object -ComObject SldWorks.Application
[GritBuildV11]::Run($sw, 'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT', 'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V13_20261003.SLDPRT')
