exec(open('work/diagnose_void_native.py',encoding='utf-8').read().split("print('solid bodies'")[0])
for name,b,bb in tools_list:
 if not any(x in name for x in ['Цилиндр внешний','01.01.00.02  Конус-']):continue
 print('COMP',name,flush=True)
 for raw in b.GetFaces() or []:
  face=typed(raw,'IFace2');fb=face.GetBox();su=typed(face.GetSurface(),'ISurface')
  if not su.IsPlane() or fb[4]-fb[1]<.3:continue
  pars=su.PlaneParams
  if face.GetArea()<.004:
   print('seam candidate','box',fb,'area',face.GetArea(),'plane',pars,flush=True)
