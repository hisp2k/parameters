param([string]$Configuration)
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using SolidWorks.Interop.sldworks;
public class CheckGritFeatureErrors {
 public static string Run(object o,string p,string cfg){var s=(ISldWorks)o;int e=0,w=0;var d=(IModelDoc2)s.OpenDoc6(p,1,0,"",ref e,ref w);bool sh=d.ShowConfiguration2(cfg);bool rb=d.ForceRebuild3(false);string result="CFG="+cfg+";SHOW="+sh+";REBUILD="+rb+";";for(var f=d.FirstFeature() as IFeature;f!=null;f=f.GetNextFeature() as IFeature){if(f.Name=="BATH_BASE_PLATE"||f.Name=="MASTER_FOOTPRINT"){bool warning=false;int code=f.GetErrorCode2(out warning);result+=f.Name+"_ERROR="+code+";WARNING="+warning+";";}}return result;}
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
[CheckGritFeatureErrors]::Run($sw,'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V8_20261003.SLDPRT',$Configuration)
