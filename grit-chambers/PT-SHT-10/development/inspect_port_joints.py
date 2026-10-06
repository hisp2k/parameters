exec(open('work/diagnose_void_native.py',encoding='utf-8').read().split("print('solid bodies'")[0])
for name,b,bb in tools_list:
 if not any(x in name for x in ['Цилиндр внешний','Труба входная','Труба внешняя','Прокладка','Крышка глухая']):continue
 print('PART',name,'box',bb,flush=True)
 for raw in b.GetFaces() or []:
  f=typed(raw,'IFace2');su=typed(f.GetSurface(),'ISurface')
  if su.IsCylinder():print(' CYL',su.CylinderParams,'box',f.GetBox(),flush=True)
  elif 'Цилиндр внешний' in name:print(' OTHER',su.Identity(),'box',f.GetBox(),'area',f.GetArea(),flush=True)
