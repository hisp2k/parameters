$ErrorActionPreference='Stop'
$dll='C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\SolidWorks.Interop.sldworks.dll'
Add-Type -Path $dll
$src=@'
using System;using System.Globalization;using SolidWorks.Interop.sldworks;
public static class GritInterferenceAudit {
 public static string Run(object o,string p){ISldWorks s=(ISldWorks)o;int e=0,w=0;IModelDoc2 d=(IModelDoc2)s.OpenDoc6(p,1,0,"",ref e,ref w);object[] a=(object[])((IPartDoc)d).GetBodies2(0,false);IBody2 screw=null;foreach(object ob in a){IBody2 b=(IBody2)ob;if(b.GetFaceCount()==3)screw=b;}if(screw==null)return d.GetTitle()+":NO_SCREW";
  int collisions=0;double total=0;string details="";foreach(object ob in a){IBody2 b=(IBody2)ob;if(b.GetFaceCount()==3)continue;int err=0;object res=((IBody2)b.Copy()).Operations2(15901,screw.Copy(),out err);if(res is object[] rs){foreach(object r in rs){double[] m=(double[])((IBody2)r).GetMassProperties(1);if(m[3]>1e-12){collisions++;total+=m[3];details+=b.GetFaceCount()+":"+m[3].ToString("G8",CultureInfo.InvariantCulture)+"|";}}}}
  return d.GetTitle()+":collisions="+collisions+":intersectionVolume="+total.ToString("G8",CultureInfo.InvariantCulture)+":details="+details;
 }
}
'@
Add-Type -TypeDefinition $src -ReferencedAssemblies $dll
$sw=New-Object -ComObject SldWorks.Application
$dir='C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\grit_chamber\01_CAD'
[GritInterferenceAudit]::Run($sw,(Join-Path $dir 'GRIT_PILOT_BASE_CAD_20261003.SLDPRT'))
[GritInterferenceAudit]::Run($sw,(Join-Path $dir 'GRIT_PILOT_NARROW_CAD_20261003.SLDPRT'))
[GritInterferenceAudit]::Run($sw,(Join-Path $dir 'GRIT_PILOT_SHORT_WIDE_CAD_20261003.SLDPRT'))
