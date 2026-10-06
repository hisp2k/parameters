exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
keys=['Сбрасыватель','Стопорное кольцо D40','Вал шнека верхний','Вал шнека нижний','Фланец обоймы','Прокладка','Шайба пружинная М8']
seen=set()
for c in doc.GetComponents(False):
 if not any(n in c.Name2 for n in keys) or c.GetPathName in seen:continue
 seen.add(c.GetPathName);d=c.GetModelDoc2
 print('COMP',c.Name2,c.GetPathName,'box',d.GetPartBox(True),'transform',list(c.Transform2.ArrayData),flush=True)
 cylinders={}
 for b in d.GetBodies2(0,False):
  for face in b.GetFaces():
   if face.GetSurface.IsCylinder:
    p=face.GetSurface.CylinderParams;radius=round(p[6]*1000,4);cylinders.setdefault(radius,[]).append(list(face.GetBox))
 print('CYLINDERS',cylinders,flush=True)
 f=d.FirstFeature
 while f:
  display=f.GetFirstDisplayDimension;dims=[]
  while display:
   dim=display.GetDimension2(0);dims.append((dim.FullName,dim.SystemValue));display=f.GetNextDisplayDimension(display)
  if dims: print('DIMS',f.Name,f.GetTypeName2,dims,flush=True)
  f=f.GetNextFeature
