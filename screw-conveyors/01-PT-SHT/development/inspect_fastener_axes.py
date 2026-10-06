exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
def cylinders(c,r):
 t=list(c.Transform2.ArrayData);rows=[]
 for b in c.GetModelDoc2.GetBodies2(0,True):
  for f in b.GetFaces():
   if not f.GetSurface.IsCylinder:continue
   p=list(f.GetSurface.CylinderParams)
   if abs(p[6]-r)>1e-6:continue
   o=[sum(p[j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)];a=[sum(p[j+3]*t[j*3+i] for j in range(3)) for i in range(3)]
   rows.append((o,a,f))
 return rows
flanges=[c for c in doc.GetComponents(False) if 'Фланец обоймы' in c.Name2]
for c in doc.GetComponents(True):
 if not c.Name2.startswith('Болт М8х25'):continue
 axes=cylinders(c,.004);assert axes
 o,a,f=axes[0];nearest=[]
 for fl in flanges:
  for p,u,face in cylinders(fl,.0044):
   delta=[o[i]-p[i] for i in range(3)];along=sum(delta[i]*a[i] for i in range(3));perp=sum((delta[i]-along*a[i])**2 for i in range(3))**.5
   nearest.append((perp,fl.Name2))
 print(c.Name2,'offset mm',min(nearest)[0]*1000,'flange',min(nearest)[1],flush=True)
for c in doc.GetComponents(True):
 if c.Name2.startswith('Болт М8х25'):
  d=c.GetModelDoc2;print('BOLT radii',sorted(set(round(f.GetSurface.CylinderParams[6]*1000,5) for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder)),flush=True);break
