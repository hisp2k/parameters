exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
for m in mates(doc):
 sp=m.GetSpecificFeature2;es=[sp.MateEntity(i) for i in range(sp.GetMateEntityCount)];ns=[e.ReferenceComponent.Name2 if e.ReferenceComponent else '' for e in es]
 if any('Обойма верхняя' in n or n.endswith('М8х25 DIN 933-9') for n in ns):
  print(m.Name,m.GetTypeName2,ns,flush=True)
  if not any('Шайба' in n or 'Гайка' in n for n in ns):
   for ent in es:print(list(ent.EntityParams),flush=True)
