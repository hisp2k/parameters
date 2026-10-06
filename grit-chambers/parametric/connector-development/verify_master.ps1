param([string]$Configuration)
$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using SolidWorks.Interop.sldworks;
public class VerifyMasterConfig {
 static double V(IEquationMgr q,string name){for(int i=0;i<q.GetCount();i++)if(q.Equation[i].StartsWith("\""+name+"\""))return q.Value[i];throw new Exception(name+" missing");}
 public static string Run(object o,string p,string cfg){var s=(ISldWorks)o;int e=0,w=0;var d=(IModelDoc2)s.OpenDoc6(p,1,0,"",ref e,ref w);bool sh=d.ShowConfiguration2(cfg);var q=(IEquationMgr)d.GetEquationMgr();var dimL=(IDimension)d.Parameter("D1@MASTER_FOOTPRINT");var dimB=(IDimension)d.Parameter("D2@MASTER_FOOTPRINT");bool rb=d.ForceRebuild3(false);return cfg+";SHOW="+sh+";B="+V(q,"AI_B_Bath")+";L_SETTLE="+V(q,"AI_L_Settle")+";L_BATH="+V(q,"AI_L_Bath")+";DIM_B_M="+dimB.SystemValue+";DIM_L_M="+dimL.SystemValue+";REBUILD="+rb;}
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
[VerifyMasterConfig]::Run($sw,'C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD\GRIT_MASTER_V8_20261003.SLDPRT',$Configuration)
