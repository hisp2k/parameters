from pathlib import Path
import sys,json,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 sw.ActivateDoc3(tube.GetPathName,False,2,e);assert not e.value
 mgr,globals_=bridge.globals_in(tube)
 unused=globals_.get('Угол транспортера к горизонтали')
 if unused:assert mgr.Delete(unused[0])
 assert bridge.model_issues(sw,top)==(0,0,[]) and not bridge.interference_issues(top)
 assert top.Save3(13,e,q) and not e.value
 state=json.loads(bridge.STATE.read_text(encoding='utf-8'));before=state['values']['incline']
 state['values']['incline']=round(bridge.measured_geometry(top)['incline'],6)
 project=json.loads((base/'project.json').read_text(encoding='utf-8'));project['target_incline_deg']=55
 (base/'project.json').write_text(json.dumps(project,ensure_ascii=False,indent=2),encoding='utf-8')
 r=bridge.apply(state['values'],sw,state['selection'],state['design_mode']);assert r['ok'],r
 print('UI angle corrected',before,'to actual',r['cad_verification']['measured_geometry']['incline'],'target remains 55',flush=True)
finally:sw.CommandInProgress=prev
