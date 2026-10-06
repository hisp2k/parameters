exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
for m in mates(doc):
 sp=m.GetSpecificFeature2;es=[sp.MateEntity(i) for i in range(sp.GetMateEntityCount)]
 if m.GetTypeName2=='MateConcentric' and any('Шайба пружинная М8' in e.ReferenceComponent.Name2 for e in es):
  print('MATE',m.Name,flush=True)
  for ent in es:print(ent.ReferenceComponent.Name2,list(ent.EntityParams),flush=True)
for name in ['Обойма верхняя','Обойма нижняя']:
 d=next(c.GetModelDoc2 for c in doc.GetComponents(True) if name in c.Name2)
 for c in d.GetComponents(True):
  if any(n in c.Name2 for n in ['Фланец','Прокладка']):
   p=c.GetModelDoc2;print('PART',c.Name2,flush=True)
   for b in p.GetBodies2(0,True):
    for f in b.GetFaces():
     surf=f.GetSurface
     if surf.IsCylinder:
      v=list(surf.CylinderParams)
      if .003<v[6]<.005:print('HOLE',v,flush=True)
