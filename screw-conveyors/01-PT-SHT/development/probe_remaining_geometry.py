exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
for name in ['Стопорное кольцо D40','Вал шнека нижний','Шайба пружинная М8','Прокладка','Кран шаровый']:
 cs=[c for c in doc.GetComponents(False) if name in c.Name2]
 if name=='Шайба пружинная М8':cs=[c for c in cs if c.Name2.endswith('-29')]
 for c in cs:
  d=c.GetModelDoc2;print('COMP',c.Name2,'transform',list(c.Transform2.ArrayData),flush=True)
  print('BBOX',[list(b.GetBodyBox()) for b in d.GetBodies2(0,True)],flush=True)
  print('CYL',[(list(f.GetSurface.CylinderParams),list(f.GetBox)) for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder],flush=True)
  if name=='Кран шаровый':
   f=d.FirstFeature
   while f:
    if f.GetTypeName2=='RefPlane':print('PLANE',f.Name,list(f.GetSpecificFeature2.Transform.ArrayData),flush=True)
    f=f.GetNextFeature
