from pathlib import Path
import sys,json,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));c=next(c for c in top.GetComponents(False) if 'Труба шнека' in c.Name2);part=c.GetModelDoc2
 f=part.FeatureByName('Вырез-Вытянуть8');data=f.GetDefinition
 print('CUT8',data.GetEndCondition(True),data.GetDepth(True),data.GetEndCondition(False),data.GetDepth(False),'both',data.BothDirections,'reverse',data.ReverseDirection,'from',data.FromType,flush=True)
 print('parents',[(x.Name,x.GetTypeName2) for x in f.GetParents or []],flush=True)
 for name in ['D1@Вырез-Вытянуть8','D1@Эскиз10','D2@Эскиз10']:
  p=part.Parameter(name);print(name,p.SystemValue if p else None,flush=True)
 ear=next(c for c in top.GetComponents(False) if 'Ухо' in c.Name2)
 for b in ear.GetModelDoc2.GetBodies2(0,True):
  for face in b.GetFaces():
   sf=face.GetSurface
   if sf.IsCylinder:print('ear cylinder',list(sf.CylinderParams),flush=True)
 for c in top.GetComponents(False):
  if 'Опора_SPCR' not in c.Name2:continue
  t=list(c.Transform2.ArrayData);planes=[]
  for b in c.GetModelDoc2.GetBodies2(0,True):
   for face in b.GetFaces():
    sf=face.GetSurface
    if sf.IsPlane:
     q=list(sf.PlaneParams);normal=[sum(q[j]*t[j*3+i] for j in range(3)) for i in range(3)];planes.append((face.GetArea,normal))
  print('ground support planes',sorted(planes,reverse=True)[:4],flush=True);break
finally:sw.CommandInProgress=prev
