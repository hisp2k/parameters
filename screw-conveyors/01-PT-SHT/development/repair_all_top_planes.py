exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
from math import dist
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(doc.GetTitle,False,2,err)
repaired=[]
old101=next(m for m in mates(doc) if m.Name=='Совпадение101')
if old101.IsSuppressed:
 new101=next(m for m in mates(doc) if m.Name=='Совпадение120')
 doc.ClearSelection2(True);old101.Select2(False,0);doc.Extension.DeleteSelection2(0);new101.Name='Совпадение101 — восстановлено';repaired.append('Совпадение101')
for old in list(mates(doc)):
 if not old.GetErrorCode or old.GetTypeName2!='MateCoincident':continue
 es=[old.GetSpecificFeature2.MateEntity(i) for i in (0,1)];cs=[e.ReferenceComponent for e in es];before=[tuple(c.Transform2.ArrayData[9:12]) for c in cs];fs=[]
 for i,ent in enumerate(es):
  if ent.Reference is not None:fs.append(old.GetDefinition.EntitiesToMate[i]);continue
  candidates=plane_candidates(ent)
  if not candidates or candidates[0][0]>1e-6 or (len(candidates)>1 and candidates[1][0]<1e-6):raise RuntimeError('Plane ambiguity '+old.Name)
  fs.append(ent.ReferenceComponent.GetCorrespondingEntity(candidates[0][1]))
 alignment=old.GetDefinition.MateAlignment;name=old.Name
 old.SetSuppression2(0,1,None);doc.ClearSelection2(True)
 data=doc.CreateMateData(0);data.MateAlignment=alignment;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,fs)
 new=doc.CreateMate(data)
 if new is None or new.GetErrorCode:raise RuntimeError('New mate failed '+name)
 shifts=[dist(p,c.Transform2.ArrayData[9:12])*1000 for p,c in zip(before,cs)];print(name,shifts,flush=True)
 if max(shifts)>30:raise RuntimeError('Movement '+name)
 doc.ClearSelection2(True)
 if not old.Select2(False,0) or not doc.Extension.DeleteSelection2(0):raise RuntimeError('Deletion failed')
 new.Name=name+' — восстановлено';repaired.append(name)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',doc.Save3(1,e,q),e.value,q.value,flush=True)
(base/'all_mate_repairs_20261004.json').write_text(json.dumps(repaired,ensure_ascii=False,indent=2),encoding='utf-8')

