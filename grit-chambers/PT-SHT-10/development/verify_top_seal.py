import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application');d=s.GetOpenDocumentByName(str(Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_top_seal_v2.SLDPRT'))
print('doc',bool(d))
if d:
 for body in d.GetBodies2(0,False) or []:
  for face in body.GetFaces() or []:
   sf=face.GetSurface
   if sf.IsCylinder:print('r',sf.CylinderParams[6])
