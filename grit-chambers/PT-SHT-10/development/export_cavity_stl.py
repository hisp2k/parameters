from pathlib import Path
import pythoncom,win32com.client as w
pythoncom.CoInitialize()
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
tis={l.GetDocumentation(i)[0]:l.GetTypeInfo(i) for i in range(l.GetTypeInfoCount())}
def typed(o,n):return w.dynamic.Dispatch(o._oleobj_ if hasattr(o,'_oleobj_') else o,typeinfo=tis[n])
s=typed(w.Dispatch('SldWorks.Application'),'ISldWorks')
doc=s.ActiveDoc
assert 'pt-sht-10-demo' in doc.GetPathName
modeler=typed(s.GetModeler(),'IModeler')
arr=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,(0.,.2,-.5,0.,0.,1.,1.,1.5,1.))
box=typed(modeler.CreateBodyFromBox(arr),'IBody2')
bodies=[box]
for c in doc.GetComponents(False) or []:
 if c.GetSuppression==0:continue
 if not any(x in c.Name2.split('/')[-1] for x in ['Цилиндр','Конус','Отвод','Труба','Фланец','Крышка глухая','Прокладка','CFD_']):continue
 raw=c.GetBody
 if not raw:continue
 tool=typed(typed(raw,'IBody2').Copy(),'IBody2')
 assert tool.ApplyTransform(c.Transform2)
 bb=list(tool.GetBodyBox());new=[]
 for target in bodies:
  tb=target.GetBodyBox()
  if any(tb[k+3]<bb[k] or bb[k+3]<tb[k] for k in range(3)):
   new.append(target);continue
  a=typed(target.Copy(),'IBody2');b=typed(tool.Copy(),'IBody2')
  result,err=a.Operations2(15902,b,0)
  if not result and err==547:
   a=typed(target.Copy(),'IBody2');b=typed(tool.Copy(),'IBody2');a.ResetEdgeTolerances();b.ResetEdgeTolerances();result,err=a.Operations2(15902,b,0)
  if result:new.extend(typed(x,'IBody2') for x in result)
  elif err in (1067,5):new.append(target)
  elif err!=0:raise RuntimeError(f'boolean error {c.Name2} {err}')
 bodies=new
print('regions',len(bodies),[(b.GetMassProperties(1.)[3],list(b.GetBodyBox())) for b in bodies],flush=True)
cavity=[b for b in bodies if abs(b.GetMassProperties(1.)[3]-.16254310539050704)<1e-6]
assert len(cavity)==1
part=s.NewPart()
assert part
feature=typed(part,'IPartDoc').CreateFeatureFromBody3(cavity[0],False,0)
assert feature
print('cavity feature created',flush=True)
out=Path('work/cavity_for_particle_model.stl').resolve()
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
ok=part.Extension.SaveAs(str(out),0,1,None,e,v)
print('export STL',ok,'errors',e.value,'warnings',v.value,'size',out.stat().st_size if out.exists() else 0,flush=True)
assert ok and out.exists()
