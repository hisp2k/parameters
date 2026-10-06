exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
for node in ['Обойма нижняя','Обойма верхняя']:
 d=next(c.GetModelDoc2 for c in doc.GetComponents(True) if node in c.Name2)
 ring=next(c for c in d.GetComponents(True) if 'Стопорное кольцо D40' in c.Name2)
 shaft=next(c for c in doc.GetComponents(False) if ('Вал шнека нижний' if 'нижняя' in node else 'Вал шнека верхний') in c.Name2)
 fullring=next(c for c in doc.GetComponents(False) if c.GetPathName==ring.GetPathName)
 t=list(shaft.Transform2.ArrayData);r=list(fullring.Transform2.ArrayData)
 print(node,'ring global origin',r[9:12],'shaft-local ring origin',[sum((r[9+i]-t[9+i])*t[j*3+i] for i in range(3)) for j in range(3)],flush=True)
 for f in mates(d):
  es=[f.GetSpecificFeature2.MateEntity(i) for i in (0,1)]
  if any('Стопорное кольцо D40' in e.ReferenceComponent.Name2 for e in es):
   print(f.Name,f.GetTypeName2,flush=True)
   for e in es:print(e.ReferenceComponent.Name2,list(e.EntityParams or []),flush=True)
