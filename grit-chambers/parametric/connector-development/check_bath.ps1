param([string]$Configuration)
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using SolidWorks.Interop.sldworks;
public class CheckBath {
 public static string Run(object o,string p,string cfg){var s=(ISldWorks)o;int e=0,w=0;var d=(IModelDoc2)s.OpenDoc6(p,1,0,"",ref e,ref w);bool show=d.ShowConfiguration2(cfg);bool rebuild=d.ForceRebuild3(false);var part=(IPartDoc)d;var bodies=(object[])part.GetBodies2(0,false);var dimL=(IDimension)d.Parameter("D1@MASTER_FOOTPRINT");var dimB=(IDimension)d.Parameter("D2@MASTER_FOOTPRINT");var dimH=(IDimension)d.Parameter("D1@BATH_BASE_PLATE");string x="CONFIG="+cfg+";SHOW="+show+";REBUILD="+rebuild+";BODIES="+bodies.Length+";L="+dimL.SystemValue+";B="+dimB.SystemValue+";H="+dimH.SystemValue+";";for(var f=d.FirstFeature() as IFeature;f!=null;f=f.GetNextFeature() as IFeature){if(f.Name=="BATH_BASE_PLATE"||f.Name=="BATH_SHELL_2MM"){bool wng=false;int code=f.GetErrorCode2(out wng);x+=f.Name+"_ERR="+code+";WARN="+wng+";";if(f.Name=="BATH_SHELL_2MM"){var shell=(IShellFeatureData)f.GetDefinition();x+="THICK="+shell.Thickness+";OPEN_FACES="+shell.FacesRemovedCount+";";}}}return x;}
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
[CheckBath]::Run($sw,'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V10_20261003.SLDPRT',$Configuration)
