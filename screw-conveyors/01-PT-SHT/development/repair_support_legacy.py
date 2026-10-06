exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
from math import dist
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
old=sw.GetOpenDocumentByName(str(Path('work/Опора — сравнение положения.SLDASM').resolve()))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(support.GetTitle,False,2,e)
original_names={m.Name for m in mates(old)}
for f in list(mates(support)):
 if f.Name in ['Расстояние5 — восстановлено','Расстояние6 — восстановлено','Расстояние8 — восстановлено','Расстояние9 — восстановлено'] or (f.GetTypeName2=='MateDistanceDim' and f.Name not in original_names):
  support.ClearSelection2(True);f.Select2(False,0);support.Extension.DeleteSelection2(0)
math=sw.GetMathUtility

math._FlagAsMethod('CreateTransform')
for c in support.GetComponents(True):
 if c.Name2.startswith('PT.SHT.01.01.02.03'):
  before=next(o for o in old.GetComponents(True) if o.Name2==c.Name2).Transform2.ArrayData
  c.Transform2=math.CreateTransform(w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,before))
for name in ['Расстояние5','Расстояние6','Расстояние8','Расстояние9']:
 original=next(m for m in mates(old) if m.Name==name);ents=[original.GetSpecificFeature2.MateEntity(i) for i in (0,1)]
 support.ClearSelection2(True);sel=support.SelectionManager.CreateSelectData;sel.Mark=1
 for ent in ents:
  comp=next(c for c in support.GetComponents(True) if c.Name2==ent.ReferenceComponent.Name2)
  if 'PT.SHT.01.01.02.03' in comp.Name2:
   if name in ['Расстояние8','Расстояние9']:
    axis='Ось отверстия пластины — восстановлено';full=axis+'@'+comp.Name2+'@'+support.GetTitle.removesuffix('.SLDASM')
    assert support.Extension.SelectByID2(full,'AXIS',0.,0.,0.,True,1,w.VARIANT(pythoncom.VT_DISPATCH,None),0)
   else:
    # Replace the lost planar face, retaining the original plane equation.
    class Entity:pass
    v=Entity();v.ReferenceComponent=comp;v.EntityParams=ent.EntityParams
    found=plane_candidates(v);assert found[0][0]<1e-6
    comp.GetCorrespondingEntity(found[0][1]).Select4(True,sel)
  else:
   ref=original.GetDefinition.EntitiesToMate[0 if name in ['Расстояние5','Расстояние6'] else 1]
   try:
    pname=ref.Name;full=pname+'@'+comp.Name2+'@'+support.GetTitle.removesuffix('.SLDASM');assert support.Extension.SelectByID2(full,'PLANE',0.,0.,0.,True,1,w.VARIANT(pythoncom.VT_DISPATCH,None),0)
   except AttributeError:
    target=list(ref.GetCurve.LineParams);matches=[]
    for body in comp.GetModelDoc2.GetBodies2(0,True):
     for edge in body.GetEdges():
      curve=edge.GetCurve
      if curve.IsLine:
       p=list(curve.LineParams)
       if max(abs(p[i]-target[i]) for i in range(6))<1e-7:matches.append(edge)
    assert len(matches)==1;comp.GetCorrespondingEntity(matches[0]).Select4(True,sel)
 status=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);distance=.02 if name in ['Расстояние5','Расстояние6'] else .05
 mate=support.AddMate5(5,2,True,distance,distance,distance,0.,0.,0.,0.,0.,False,False,0,status)
 print(name,'status',status.value,'result',mate,flush=True)
 if status.value!=1 or mate is None:raise RuntimeError('Mate creation failed')
 f=list(mates(support))[-1];f.Name=name+' — восстановлено'
math=sw.GetMathUtility

math._FlagAsMethod('CreateTransform')
for c in support.GetComponents(True):
 if c.Name2.startswith('PT.SHT.01.01.02.03'):
  oldc=next(o for o in old.GetComponents(True) if o.Name2==c.Name2)
  print(c.Name2,'position change',dist(oldc.Transform2.ArrayData[9:12],c.Transform2.ArrayData[9:12])*1000,'rotation change',max(abs(a-b) for a,b in zip(oldc.Transform2.ArrayData[:9],c.Transform2.ArrayData[:9])),flush=True)
print('save',support.Save3(1,e,q),e.value,q.value,flush=True)
doc.ForceRebuild3(False);print('top save',doc.Save3(1,e,q),e.value,q.value,flush=True)





