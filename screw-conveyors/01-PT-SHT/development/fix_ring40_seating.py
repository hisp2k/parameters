exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
for side,offset in [('верхний',.001775),('нижний',.003975)]:
 d=next(c.GetModelDoc2 for c in doc.GetComponents(False) if f'Вал шнека {side}' in c.Name2)
 sw.ActivateDoc3(d.GetTitle,False,2,e)
 for name,value in [('D1@Плоскость2',offset),('D1@Вырез-Вытянуть1',.00185),('D1@Эскиз4',.0375),('D1@Скругление1',.00005)]:
  dim=d.Parameter(name);assert dim is not None,name;dim.SystemValue=value
 d.ForceRebuild3(False);f=d.FirstFeature;errors=[]
 while f:
  if f.GetErrorCode:errors.append((f.Name,f.GetErrorCode))
  f=f.GetNextFeature
 assert not errors,errors
 assert d.Save3(1,e,q);print('shaft',side,'saved',flush=True)
d=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Обойма верхняя' in c.Name2)
sw.ActivateDoc3(d.GetTitle,False,2,e)
old=next(f for f in mates(d) if f.Name=='Концентричный17');es=[old.GetSpecificFeature2.MateEntity(i) for i in (0,1)]
ring=es[1].ReferenceComponent;bearing=es[0].ReferenceComponent
def cyl(c,r):
 fs=[f for b in c.GetModelDoc2.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder and abs(f.GetSurface.CylinderParams[6]-r)<1e-7]
 assert fs;return c.GetCorrespondingEntity(fs[0])
alignment=old.GetDefinition.MateAlignment;old.SetSuppression2(0,1,None)
data=d.CreateMateData(1);data.MateAlignment=alignment;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[cyl(bearing,.02),cyl(ring,.01875)])
new=d.CreateMate(data);assert new and not new.GetErrorCode
d.ClearSelection2(True);assert old.Select2(False,0);assert d.Extension.DeleteSelection2(0);new.Name='Кольцо D40 — соосность посадочной окружности'
d.ForceRebuild3(False);assert not [(m.Name,m.GetErrorCode) for m in mates(d) if m.GetErrorCode];assert d.Save3(1,e,q)
sw.ActivateDoc3(doc.GetTitle,False,2,e);doc.ForceRebuild3(False)
assert not [(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode];assert doc.Save3(1,e,q)
print('ring and top saved',flush=True)
