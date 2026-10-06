exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import math,shutil
cs=[(c.Name2,c) for c in doc.GetComponents(False)];parts={c.GetPathName:c.GetModelDoc2 for n,c in cs if 'Прокладка' in n};e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
backup=base/'snapshots/20261004-before-gasket-hole-fix';backup.mkdir(parents=True,exist_ok=True)
for path,d in parts.items():
 shutil.copy2(path,backup/Path(path).name);sw.ActivateDoc3(d.GetTitle,False,2,e)
 before=sum(b.GetMassProperties(1)[3] for b in d.GetBodies2(0,True));holes=[]
 for b in d.GetBodies2(0,True):
  for f in b.GetFaces():
   surf=f.GetSurface
   if surf.IsCylinder:
    v=list(surf.CylinderParams)
    if abs(v[6]-.0044)<1e-7:holes.append(v)
 assert len(holes)==8
 for j,v in enumerate(holes):
  angle=round(math.atan2(v[2],v[1])/(math.pi/4))*math.pi/4;target=[v[0],.085*math.cos(angle),.085*math.sin(angle)];delta=[target[k]-v[k] for k in range(3)]
  if sum(x*x for x in delta)<1e-20:continue
  candidates=[]
  for b in d.GetBodies2(0,True):
   for f in b.GetFaces():
    sf=f.GetSurface
    if sf.IsCylinder:
     u=list(sf.CylinderParams)
     if abs(u[6]-.0044)<1e-7 and abs(u[1]-v[1])+abs(u[2]-v[2])<1e-8:candidates.append(f)
  assert len(candidates)==1;d.ClearSelection2(True);sel=d.SelectionManager.CreateSelectData;sel.Mark=1;assert candidates[0].Select4(False,sel)
  f=d.FeatureManager.InsertMoveFace3(1,False,0.,0.,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,delta),None,0,0.);assert f and not f.GetErrorCode;f.Name=f'Отверстие {j+1} — окружность 170 мм';print('hole moved',j+1,[round(x*1000,4) for x in delta],flush=True)
 d.ForceRebuild3(False);after=sum(b.GetMassProperties(1)[3] for b in d.GetBodies2(0,True));assert abs(after-before)<1e-12;assert d.Save3(1,e,q);print('gasket saved',Path(path).name,flush=True)
parents={doc.GetPathName:doc}
for _,c in cs:
 d=c.GetModelDoc2
 if d and d.GetType==2:parents[d.GetPathName]=d
for d in parents.values():d.ForceRebuild3(False)
sw.ActivateDoc3(doc.GetTitle,False,2,e);doc.ForceRebuild3(False)
for d in parents.values():assert d.Save3(1,e,q)
print('gaskets complete',flush=True)
