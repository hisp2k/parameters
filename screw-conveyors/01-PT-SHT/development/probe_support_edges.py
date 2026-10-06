exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
for m in mates(support):
 if m.Name in ['Расстояние8','Расстояние9','Расстояние5 — восстановлено']:
  print(m.Name)
  for i in (0,1):
   ent=m.GetSpecificFeature2.MateEntity(i);print(i,'type',ent.ReferenceType2,'ref',ent.Reference,'params',list(ent.EntityParams))
   if ent.Reference is None:
    c=ent.ReferenceComponent
    for body in c.GetModelDoc2.GetBodies2(0,True):
     for edge in body.GetEdges():
      curve=edge.GetCurve
      if curve.IsLine:print('line',curve.LineParams)
