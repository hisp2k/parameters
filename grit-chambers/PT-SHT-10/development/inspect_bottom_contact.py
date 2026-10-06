exec(open('work/diagnose_void_native.py',encoding='utf-8').read().split("print('solid bodies'")[0])
for name,b,bb in tools_list:
 if not any(x in name for x in ['01.01.00.02  Конус-','01.01.00.05  Отвод-']):continue
 print('COMP',name,'box',bb,flush=True)
 for face in b.GetFaces() or []:
  fb=face.GetBox
  if fb[1]>.04:continue
  su=face.GetSurface
  kind='plane' if su.IsPlane else 'cylinder' if su.IsCylinder else 'cone' if su.IsCone else 'other'
  pars=su.PlaneParams if kind=='plane' else su.CylinderParams if kind=='cylinder' else su.ConeParams if kind=='cone' else None
  print(kind,'box',fb,'area',face.GetArea,'params',pars,flush=True)
