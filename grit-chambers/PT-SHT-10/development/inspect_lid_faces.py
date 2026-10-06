import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application');p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
d=s.GetOpenDocumentByName(str(p))
for comp in d.GetComponents(False) or []:
 if 'CFD_крышка' not in comp.Name2:continue
 print('\nCOMP',comp.Name2,list(comp.GetBox(False,False)))
 body=comp.GetBody
 print('body',body)
 for i,face in enumerate(body.GetFaces() or []):
  surf=face.GetSurface
  print(' FACE',i,'plane',surf.IsPlane,'area',face.GetArea,'box',face.GetBox if hasattr(face,'GetBox') else None)
  if surf.IsPlane:print('  param',surf.PlaneParams)
