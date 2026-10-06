from pathlib import Path
import json,pythoncom,sys
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sw=w.GetActiveObject('SldWorks.Application')
path=Path(json.loads((base/'recovered_assembly_check.json').read_text(encoding='utf-8'))['assembly']);doc=sw.GetOpenDocumentByName(str(path))
def mates(d):
 f=d.FirstFeature
 while f:
  if f.GetTypeName2=='MateGroup':
   m=f.GetFirstSubFeature
   while m:
    yield m;m=m.GetNextSubFeature
  f=f.GetNextFeature

def plane_candidates(ent):
 c=ent.ReferenceComponent;t=list(c.Transform2.ArrayData);p=list(ent.EntityParams);matches=[]
 for body in c.GetModelDoc2.GetBodies2(0,True):
  for face in body.GetFaces():
   if not face.GetSurface.IsPlane:continue
   q=list(face.GetSurface.PlaneParams)
   n=[sum(q[j]*t[j*3+i] for j in range(3)) for i in range(3)];o=[sum(q[j+3]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]
   dot=sum(n[i]*p[3+i] for i in range(3));distance=abs(sum((o[i]-p[i])*p[3+i] for i in range(3)))
   if abs(dot)>.99999:matches.append((distance,face,dot,face.GetArea))
 return sorted(matches,key=lambda a:a[0])
for m in mates(doc):
 if m.GetErrorCode and m.GetTypeName2=='MateCoincident':
  print(m.Name)
  for i in (0,1):
   ent=m.GetSpecificFeature2.MateEntity(i)
   if ent.Reference is None:print(i,ent.ReferenceComponent.Name2,[(round(d*1000,5),round(dot,2),round(area*1e6,2)) for d,_,dot,area in plane_candidates(ent)][:9])
