from pathlib import Path
import pythoncom,win32com.client as w,json
pythoncom.CoInitialize();lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
tis={lib.GetDocumentation(i)[0]:lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount())}
def typed(o,n):return w.dynamic.Dispatch(o._oleobj_ if hasattr(o,'_oleobj_') else o,typeinfo=tis[n])
s=typed(w.Dispatch('SldWorks.Application'),'ISldWorks');base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'
a=s.GetOpenDocumentByName(str(next(base.glob('*Бункер в сборе.SLDASM'))));s.ActivateDoc3(a.GetTitle,False,0,0)
assert 'pt-sht-10-demo' in a.GetPathName
replaced=['Цилиндр внешний','01.01.00.02  Конус-','01.01.00.05  Отвод-','Крышка глухая']
log=[];a.ClearSelection2(True)
for c in a.GetComponents(False) or []:
 if c.GetSuppression==0 or not c.GetBody:continue
 leaf=c.Name2.split('/')[-1]
 keep=any(x in leaf for x in ['Цилиндр','Конус','Отвод','Труба','Фланец','Крышка глухая','Прокладка','CFD_'])
 if any(x in leaf for x in replaced) or not keep:
  status=c.Select4(True,w.VARIANT(pythoncom.VT_DISPATCH,None),False);log.append({'component':c.Name2,'selected':status})
print('BATCH SUPPRESS',len(log),a.EditSuppress2 if log else 'already suppressed',flush=True)
mu=typed(s.GetMathUtility(),'IMathUtility')
mat=mu.CreateTransform(w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,(1.,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.,1.,0.,0.,0.)))
for name in ['CFD_cylinder_welded','CFD_cone_welded','CFD_bottom_pipe_extended','CFD_top_cover_sealed']:
 existing=next((x for x in a.GetComponents(False) if x.Name2.startswith(name+'-')),None)
 c=typed(existing if existing else a.AddComponent4(str(base/(name+'.SLDPRT')),'',0.,0.,0.),'IComponent2')
 print('ADD',c.Name2,'transform',c.SetTransformAndSolve2(mat),flush=True)
 print('TRANSFORM',list(c.Transform2.ArrayData),flush=True)
 assert max(abs(v) for v in c.Transform2.ArrayData[9:12])<1e-8
 a.ClearSelection2(True);c.Select4(False,None,False);a.FixComponent
 print('BOX',list(c.GetBox(False,False)),flush=True)
print('REBUILD',a.ForceRebuild3(False),flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);wr=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('SAVE',a.Save3(1,e,wr),e.value,wr.value,flush=True)
(Path('work')/'weld_repair_changes.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
