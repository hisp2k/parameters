exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
names=['Ограничитель верхний','Мотор-редуктор','Винт М12','Шайба пружинная М12','Шпонка']
for c in doc.GetComponents(True):
 if any(n in c.Name2 for n in names):
  d=c.GetModelDoc2
  print('COMP',c.Name2,c.GetPathName,list(c.Transform2.ArrayData),'box',d.GetPartBox(True),flush=True)
  for b in d.GetBodies2(0,False):print('BODY',b.Name,b.Visible,flush=True)
  f=d.FirstFeature
  while f:
   if f.GetTypeName2 in ['Boss','Extrusion','Cut','HoleWzd','Revolution']:print('FEATURE',f.Name,f.GetTypeName2,flush=True)
   f=f.GetNextFeature
for f in mates(doc):
 m=f.GetSpecificFeature2;es=[m.MateEntity(i) for i in range(m.GetMateEntityCount)]
 if any(any(n in e.ReferenceComponent.Name2 for n in names) for e in es):
  print('MATE',f.Name,f.GetTypeName2,flush=True)
  for e in es:print(e.ReferenceComponent.Name2,list(e.EntityParams or []),flush=True)
