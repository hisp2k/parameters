exec(open('work/assemble_lower_candidate.py',encoding='utf-8').read().split('oldseal=next')[0])
from math import dist

def recover(ent,existing):
 if ent.Reference is not None:return existing
 c=ent.ReferenceComponent;t=list(c.Transform2.ArrayData);p=list(ent.EntityParams);matches=[]
 for body in c.GetModelDoc2.GetBodies2(0,True):
  for face in body.GetFaces():
   if not face.GetSurface.IsPlane:continue
   q=list(face.GetSurface.PlaneParams)
   n=[sum(q[j]*t[j*3+i] for j in range(3)) for i in range(3)]
   o=[sum(q[j+3]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]
   if abs(sum(n[i]*p[3+i] for i in range(3)))>.99999 and abs(sum((o[i]-p[i])*p[3+i] for i in range(3)))<1e-7:matches.append(face)
 if len(matches)!=1:raise RuntimeError(f'Ambiguous plane {c.Name2}: {len(matches)}')
 return c.GetCorrespondingEntity(matches[0])
for name in ['Совпадение48','Совпадение49','Совпадение50','Совпадение58']:
 old=next(f for f in mates() if f.Name==name);es=[old.GetSpecificFeature2.MateEntity(i) for i in (0,1)]
 cs=[e.ReferenceComponent for e in es];before=[tuple(c.Transform2.ArrayData[9:12]) for c in cs]
 fs=[recover(e,old.GetDefinition.EntitiesToMate[i]) for i,e in enumerate(es)]
 alignment=old.GetDefinition.MateAlignment
 old.SetSuppression2(0,1,None)
 new=add(fs[0],fs[1],0,alignment,name+' — восстановлено')
 shifts=[dist(p,c.Transform2.ArrayData[9:12])*1000 for p,c in zip(before,cs)]
 print(name,'shifts',shifts,'err',new.GetErrorCode,flush=True)
 if max(shifts)>.01:raise RuntimeError('Movement exceeds 0.01mm')
 remove(old)
print('errors',[(f.Name,f.GetErrorCode) for f in mates() if f.GetErrorCode],flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',doc.Save3(1,e,q),e.value,q.value,flush=True)
