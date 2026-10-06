from pathlib import Path
import win32com.client as w
sw=w.GetActiveObject('SldWorks.Application')
d=sw.GetOpenDocumentByName(str(Path('work/Шнек — проверка замены нижней обоймы.SLDASM').resolve()))
f=d.FirstFeature
while f:
 if f.GetTypeName2=='MateGroup':
  m=f.GetFirstSubFeature
  while m:
   if m.Name=='Концентричный97':
    print('align',m.GetDefinition.MateAlignment)
    for i in (0,1):
     ent=m.GetSpecificFeature2.MateEntity(i);c=ent.ReferenceComponent
     print(i,c.Name2,'path',c.GetPathName,'ref',ent.Reference,'params',list(ent.EntityParams or []))
     for body in c.GetModelDoc2.GetBodies2(0,True):
      for face in body.GetFaces():
       if face.GetSurface.IsCylinder:print('cylinder',list(face.GetSurface.CylinderParams))
   m=m.GetNextSubFeature
 f=f.GetNextFeature
