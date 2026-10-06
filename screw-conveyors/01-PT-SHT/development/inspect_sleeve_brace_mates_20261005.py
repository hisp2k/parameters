from pathlib import Path
import json,sys,pythoncom,win32com.client as w
from brace_clearance_20261005 import world_point,local_point,unit
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));support=sw.GetOpenDocumentByName(str(bridge.FILES['support']));tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
def relevant(n):return any(t in n for t in (".25.00.05 ",".25.00.09", "'Ухо'"))
def mates(d):
 f=d.FirstFeature
 while f:
  if f.GetTypeName2=='MateGroup':
   m=f.GetFirstSubFeature
   while m:
    yield m;m=m.GetNextSubFeature
  f=f.GetNextFeature
rows=[]
for label,doc in [('top',top),('support',support),('tube',tube)]:
 for f in mates(doc):
  mate=f.GetSpecificFeature2
  if not mate:continue
  ents=[]
  for i in range(mate.GetMateEntityCount):
   e=mate.MateEntity(i);c=e.ReferenceComponent
   ents.append({'component':c.Name2 if c else None,'params':list(e.EntityParams or []),'ref_present':e.Reference is not None})
  if any(relevant(e['component'] or '') for e in ents):rows.append({'assembly':label,'name':f.Name,'type':f.GetTypeName2,'error':f.GetErrorCode,'suppressed':bool(f.IsSuppressed),'alignment':mate.Alignment,'entities':ents})
components=[]
for c in top.GetComponents(False):
 if not relevant(c.Name2):continue
 p=c.GetModelDoc2;t=list(c.Transform2.ArrayData);cyl=[];planes=[]
 for b in p.GetBodies2(0,True):
  for f in b.GetFaces():
   s=f.GetSurface
   if s.IsCylinder:
    a=list(s.CylinderParams);direction=[sum(a[3+j]*t[j*3+i] for j in range(3)) for i in range(3)]
    cyl.append({'diameter_mm':a[6]*2000,'point':world_point(a[:3],t),'axis':direction,'area_mm2':f.GetArea*1e6})
   if s.IsPlane:
    a=list(s.PlaneParams);planes.append({'point':world_point(a[3:6],t),'normal':[sum(a[j]*t[j*3+i] for j in range(3)) for i in range(3)],'area_mm2':f.GetArea*1e6})
 components.append({'name':c.Name2,'file':c.GetPathName,'fixed':bool(c.IsFixed),'transform':t,'cylinders':cyl,'planes':planes})
proof={'components':components,'mates':rows};(base/'sleeve_brace_mates_before_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
for c in components:print('COMP',c['name'],'fixed',c['fixed'],'cyl',c['cylinders'],flush=True)
for r in rows:print('MATE',r['assembly'],r['name'],r['type'],r['error'],[(e['component'],e['params']) for e in r['entities']],flush=True)
