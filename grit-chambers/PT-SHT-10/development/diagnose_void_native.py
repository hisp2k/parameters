from pathlib import Path
import pythoncom,win32com.client as w,json,time,sys
pythoncom.CoInitialize()
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
tis={l.GetDocumentation(i)[0]:l.GetTypeInfo(i) for i in range(l.GetTypeInfoCount())}
def typed(o,n):return w.dynamic.Dispatch(o._oleobj_ if hasattr(o,'_oleobj_') else o,typeinfo=tis[n])
s=typed(w.Dispatch('SldWorks.Application'),'ISldWorks');s.RunCommand(-1,'')
doc=s.ActiveDoc
print('doc',doc.GetPathName,flush=True)
assert 'pt-sht-10-demo' in doc.GetPathName
modeler=typed(s.GetModeler(),'IModeler')
arr=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,(0.,.2,-.5,0.,0.,1.,1.,1.5,1.))
box=typed(modeler.CreateBodyFromBox(arr),'IBody2')
print('box',box.GetBodyBox(),'faults',typed(box.Check3,'IFaultEntity').Count,flush=True)
bodies=[box];tools_list=[];log=[]
for c in doc.GetComponents(False) or []:
 if c.GetSuppression==0:continue
 if '--wetted-only' in sys.argv and not any(x in c.Name2.split('/')[-1] for x in ['Цилиндр','Конус','Отвод','Труба','Фланец','Крышка глухая','Прокладка','CFD_']):continue
 raw=c.GetBody
 if not raw:continue
 b=typed(raw,'IBody2');cp=typed(b.Copy(),'IBody2')
 if not cp.ApplyTransform(c.Transform2):raise RuntimeError('transform '+c.Name2)
 bounds=list(cp.GetBodyBox());cb=list(c.GetBox(False,False))
 delta=max(abs(x-y) for x,y in zip(bounds,cb))
 center_delta=max(abs((bounds[k]+bounds[k+3])/2-(cb[k]+cb[k+3])/2) for k in range(3))
 if center_delta>0.02:raise RuntimeError('transform center mismatch '+c.Name2+' '+str(center_delta))
 check=typed(cp.Check3,'IFaultEntity').Count
 if check:raise RuntimeError('invalid body '+c.Name2+' '+str(check))
 if check or delta>0.03:print('body',c.Name2,'faults',check,'box difference',delta,flush=True)
 tools_list.append((c.Name2,cp,bounds))
print('solid bodies',len(tools_list),flush=True)
for n,(name,tool,bb) in enumerate(tools_list):
 new=[]
 for target in bodies:
  tb=target.GetBodyBox()
  if any(tb[k+3]<bb[k] or bb[k+3]<tb[k] for k in range(3)):
   new.append(target);continue
  a=typed(target.Copy(),'IBody2');b=typed(tool.Copy(),'IBody2')
  try:
   result,err=a.Operations2(15902,b,0)
   if not result and err==547:
    a=typed(target.Copy(),'IBody2');b=typed(tool.Copy(),'IBody2')
    a.ResetEdgeTolerances();b.ResetEdgeTolerances()
    result,err=a.Operations2(15902,b,0)
   if result:
    new.extend(typed(x,'IBody2') for x in result)
   elif err in (1067,5):new.append(target)
   elif err==0:pass
   else:
    new.append(target);log.append({'component':name,'error':err});print('BOOLEAN ERROR',name,err,flush=True)
  except Exception as exc:
   new.append(target);log.append({'component':name,'error':repr(exc)});print('EXCEPTION',name,repr(exc),flush=True)
 bodies=new
 print('step',n+1,'of',len(tools_list),'regions',len(bodies),name,flush=True)
out=[]
for i,b in enumerate(bodies):
 mp=b.GetMassProperties(1.);bb=list(b.GetBodyBox())
 row={'region':i,'volume_m3':mp[3],'box':bb,'centroid':list(mp[:3]),'faults':typed(b.Check3,'IFaultEntity').Count};out.append(row)
 print('REGION',json.dumps(row,ensure_ascii=False),flush=True)
suffix='_wetted' if '--wetted-only' in sys.argv else ''
(Path('work')/('native_void_diagnostic'+suffix+'.json')).write_text(json.dumps({'regions':out,'errors':log},ensure_ascii=False,indent=2),encoding='utf-8')
