import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application');d=s.GetOpenDocumentByName(str(next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Прокладка.SLDPRT'))))
print('part',d.GetPathName,'box',d.GetPartBox(True))
for body in d.GetBodies2(0,False) or []:
 for face in body.GetFaces() or []:
  sf=face.GetSurface
  if sf.IsCylinder:
   q=sf.CylinderParams
   if q[6]>0.2:print('cyl r',q[6],'box',face.GetBox)
