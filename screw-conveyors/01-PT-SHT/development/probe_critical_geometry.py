exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
seen=set()
for c in doc.GetComponents(False):
 if not any(x in c.Name2 for x in ["'Винт шнека'","'Вал шнека верхний'","'Обойма'","'Ограничитель верхний'","'Сбрасыватель'"]):continue
 p=c.GetPathName
 if p in seen:continue
 seen.add(p);d=c.GetModelDoc2
 print('\nPART',c.Name2,p,flush=True)
 print('transform',list(c.Transform2.ArrayData),flush=True)
 bodies=d.GetBodies2(0,True) or [];print('bodies',len(bodies),flush=True)
 radii=set()
 for b in bodies:
  for f in b.GetFaces():
   if f.GetSurface.IsCylinder:radii.add(round(float(f.GetSurface.CylinderParams[6])*1000,3))
 print('radii',sorted(radii),flush=True)
 eq=d.GetEquationMgr
 if eq:
  for i in range(eq.GetCount):print('EQ',eq.Equation(i),flush=True)
