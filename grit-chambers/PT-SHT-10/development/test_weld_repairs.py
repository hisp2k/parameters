exec(open('work/diagnose_void_native.py',encoding='utf-8').read().split("print('solid bodies'")[0])
def array(v):return w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,v)
def cyl(r,y,h):return typed(modeler.CreateBodyFromCyl(array((0.,y,0.,0.,1.,0.,r,h))),'IBody2')
def cylinder(x,y,z,dx,dy,dz,r,h):return typed(modeler.CreateBodyFromCyl(array((x,y,z,dx,dy,dz,r,h))),'IBody2')
def cone(r1,r2,y,h):return typed(modeler.CreateBodyFromCone(array((0.,y,0.,0.,1.,0.,r1,r2,h))),'IBody2')
def op(a,b,code):
 result,err=typed(a.Copy(),'IBody2').Operations2(code,typed(b.Copy(),'IBody2'),0)
 if not result or err:raise RuntimeError('boolean '+str(code)+' error '+str(err))
 return [typed(x,'IBody2') for x in result]
def cuboid(x0,y0,z0,x1,y1,z1):
 return typed(modeler.CreateBodyFromBox(array(((x0+x1)/2,(y0+y1)/2,z0,0.,0.,1.,x1-x0,y1-y0,z1-z0))),'IBody2')
newtools=[];repaired=[]
for name,b,bb in tools_list:
 if 'Цилиндр внешний' in name:
  seal=cuboid(.2969,.3829,-.0001,.3001,.8331,.0006)
  b=op(b,seal,15903)[0]
  shell=op(cyl(.3001,.3829,.4502),cyl(.2969,.3829,.4502),15902)[0]
  for bounds,center,r in [((.21,.68,.08,.291,.76,.22),(.2515,.7195,0.),.02845),((-.045,.413,.288,.045,.503,.311),(0.,.458,0.),.03795)]:
   patch=op(shell,cuboid(*bounds),15901)[0]
   patch=op(patch,cylinder(*center,0.,0.,1.,r,.4),15902)[0]
   b=op(b,patch,15903)[0]
  repaired.append(('CFD_cylinder_welded',b))
  print('CYLINDER repaired',b.GetMassProperties(1.)[3],flush=True)
 if '01.01.00.02  Конус-' in name:
  ring=op(cone(.05405,.30147,.0329,.352),cone(.05015,.29757,.0329,.352),15902)[0]
  seal=op(ring,cuboid(-.0029,.0328,-.31,.0002,.385,.0),15901)[0]
  b=op(b,seal,15903)[0];repaired.append(('CFD_cone_welded',b))
  print('CONE repaired',b.GetMassProperties(1.)[3],flush=True)
 if '01.01.00.05  Отвод-' in name:
  b=op(cyl(.054,.003,.033),cyl(.051,.003,.033),15902)[0];repaired.append(('CFD_bottom_pipe_extended',b))
  print('BOTTOM pipe extended',b.GetMassProperties(1.)[3],flush=True)
 if 'Крышка глухая' in name:
  for x,z in [(.06,.25),(-.06,.25),(.06,-.25),(-.06,-.25)]:
   b=op(b,cylinder(x,.8359,z,0.,1.,0.,.0035,.0032),15903)[0]
  repaired.append(('CFD_top_cover_sealed',b))
 newtools.append((name,b,list(b.GetBodyBox())))
tools_list=newtools
src=open('work/diagnose_void_native.py',encoding='utf-8').read()
exec("print('solid bodies'"+src.split("print('solid bodies'",1)[1].replace("'native_void_diagnostic'","'native_void_welded'"))
if '--save-repairs' in sys.argv:
 base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'
 for name,b in repaired:
  part=s.NewDocument(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot',0,0,0)
  feat=typed(part,'IPartDoc').CreateFeatureFromBody3(b,False,0)
  if not feat:raise RuntimeError('create body feature '+name)
  path=base/(name+'.SLDPRT');part.SaveAs3(str(path),0,0)
  print('SAVED',str(path),path.stat().st_size,flush=True)
