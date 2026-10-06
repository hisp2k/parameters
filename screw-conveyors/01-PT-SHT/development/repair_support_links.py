exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
from math import dist
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(support.GetTitle,False,2,e)
for old in list(mates(support)):
 if not old.GetErrorCode:continue
 es=[old.GetSpecificFeature2.MateEntity(i) for i in (0,1)];fs=[];cs=[a.ReferenceComponent for a in es];before=[tuple(c.Transform2.ArrayData[9:12]) for c in cs]
 for i,ent in enumerate(es):
  if ent.Reference is not None:fs.append(old.GetDefinition.EntitiesToMate[i]);continue
  candidates=plane_candidates(ent)
  if not candidates or candidates[0][0]>1e-6:raise RuntimeError('Ambiguous face')
  fs.append(ent.ReferenceComponent.GetCorrespondingEntity(candidates[0][1]))
 typ=0 if old.GetTypeName2=='MateCoincident' else 5
 data=support.CreateMateData(typ);data.MateAlignment=old.GetSpecificFeature2.Alignment
 if typ==5:data.IsAdvancedMate=False;data.Distance=old.GetDefinition.Distance;data.FlipDimension=old.GetDefinition.FlipDimension
 data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,fs)
 old.SetSuppression2(0,1,None);name=old.Name
 new=support.CreateMate(data)
 if new is None or new.GetErrorCode:
  old.SetSuppression2(1,1,None);raise RuntimeError('Mate failed '+name)
 print(name,'shifts',[dist(p,c.Transform2.ArrayData[9:12])*1000 for p,c in zip(before,cs)],flush=True)
 support.ClearSelection2(True);old.Select2(False,0);support.Extension.DeleteSelection2(0);new.Name=name+' — восстановлено'
print('save',support.Save3(1,e,q),e.value,q.value,flush=True)
doc.ForceRebuild3(False);print('save top',doc.Save3(1,e,q),e.value,q.value,flush=True)
