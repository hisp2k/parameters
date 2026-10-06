from pathlib import Path
import sys,json,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));support=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
sc=next(c for c in top.GetComponents(True) if 'Опора шнековая' in c.Name2);print('Support solving',sc.Solving,'fixed',sc.IsFixed,flush=True)
def mates(d):
 f=d.FirstFeature
 while f:
  if f.GetTypeName2=='MateGroup':
   m=f.GetFirstSubFeature
   while m:
    yield m;m=m.GetNextSubFeature
  f=f.GetNextFeature
for label,doc in [('top',top),('support',support)]:
 for f in mates(doc):
  m=f.GetSpecificFeature2
  if not m:continue
  es=[m.MateEntity(i) for i in range(m.GetMateEntityCount)]
  if label=='top' and not any(e.ReferenceComponent and 'Опора шнековая' in e.ReferenceComponent.Name2 for e in es):continue
  if label=='support' and f.Name not in ['Расстояние4','Параллельность2','Совпадение15','Совпадение16','Совпадение17']:continue
  d=f.GetDefinition
  print('Mate',label,f.Name,f.GetTypeName2,'Err',f.GetErrorCode,'Suppressed',f.IsSuppressed,flush=True)
  for e,ref in zip(es,d.EntitiesToMate or []):
   try:refname=ref.Name
   except Exception:refname=None
   try:reftype=ref.GetTypeName2
   except Exception:reftype=None
   print('Ent',e.ReferenceComponent.Name2 if e.ReferenceComponent else None,'type',e.ReferenceType2,'name',refname,'featuretype',reftype,'params',e.EntityParams,flush=True)
  if f.GetTypeName2=='MateDistanceDim':print('Distance',d.Distance,flush=True)
