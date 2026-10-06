from pathlib import Path
from datetime import datetime
import sys,json,shutil,pythoncom,win32com.client as w
from brace_bypass_20261005 import create_bypass
from brace_clearance_20261005 import create_clearance
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge,journal,server
sw=w.GetActiveObject('SldWorks.Application');state=json.loads(bridge.STATE.read_text(encoding='utf-8'));assert state['values']['incline']==55
geometry=json.loads(Path('work/brace_clearance_geometry_20261005.json').read_text(encoding='utf-8'))
original=bridge.interference_issues;done=False;modified=False;native=None;proof={}
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)

def activate(part):
 sw.ActivateDoc3(part.GetPathName,False,2,e);assert not e.value

def cleanup(part):
 activate(part)
 names=['Проход корпуса — выборка для 55 градусов','Проход корпуса — профиль','Проход корпуса — поперечная плоскость','Ось корпуса 55 градусов — базовые точки']+[n+s for n in ['Полость обхода — нижний переход','Полость обхода — наружная ветвь','Полость обхода — верхний переход','Обход корпуса — нижний переход','Обход корпуса — наружная ветвь','Обход корпуса — верхний переход'] for s in ['', ' — профиль']]
 for name in names:
  f=part.FeatureByName(name)
  if f:
   part.ClearSelection2(True);assert f.Select2(False,0);assert part.Extension.DeleteSelection2(0)
 assert part.ForceRebuild3(False) and len(part.GetBodies2(0,True))==1

def repair(top):
 global done,modified,native,proof
 if done:return original(top)
 component=next(c for c in top.GetComponents(False) if "'Подкос 1'" in c.Name2);native=component.GetModelDoc2
 trial_path=(Path('work')/datetime.now().strftime('Подкос — переход 30 мм — %Y%m%d-%H%M%S.SLDPRT')).resolve();shutil.copy2(native.GetPathName,trial_path)
 spec=sw.GetOpenDocSpec(str(trial_path));spec.DocumentType=1;spec.Silent=True;trial=sw.OpenDoc7(spec);assert trial
 cleanup(trial);bypass=create_bypass(sw,trial,geometry['center'],geometry['axis']);cut=create_clearance(sw,trial,geometry['center'],geometry['axis'])
 assert len(trial.GetBodies2(0,True))==1;assert trial.Save3(9,e,q) and not e.value
 print('Isolated transition verified',bypass,flush=True);sw.CloseDoc(trial.GetTitle)
 modified=True;cleanup(native);live_bypass=create_bypass(sw,native,geometry['center'],geometry['axis']);live_cut=create_clearance(sw,native,geometry['center'],geometry['axis'])
 assert len(native.GetBodies2(0,True))==1
 activate(top);assert top.ForceRebuild3(False);assert bridge.model_issues(sw,top)==(0,0,[])
 done=True;remaining=original(top);print('Live transition intersections',remaining,flush=True)
 proof={'part':native.GetPathName,'trial':str(trial_path),'bypass':live_bypass,'cut':live_cut,'removed_contact_location':json.loads((base/'brace_ear_interference_location_20261005.json').read_text(encoding='utf-8'))}
 return remaining
try:
 bridge.interference_issues=repair;result=bridge.apply(state['values'],sw,state['selection'],state['design_mode']);assert done and result['ok']
 proof['result']=result;(base/'brace_transition_fix_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
 server.save_apply_outcome(state,result)
 journal._append({'type':'model_change','title':'Переход подкосов с зазором к ушам при изменении угла','repair_id':'brace-transition-30mm-20261005','change_count':1,'changes':[{'key':'brace_transition','name':'Начало обхода корпуса','before':'25 мм от крепёжного торца; контакт с ухом при 35°','after':'30 мм; непрерывность сохранена, зеркальный подкос обновлён; прочность требует расчёта'}]})
 print('Transition saved at target angle',result['cad_verification'],flush=True)
except Exception:
 bridge.interference_issues=original
 if modified:
  cleanup(native);create_bypass(sw,native,geometry['center'],geometry['axis'],start_margin=.010);create_clearance(sw,native,geometry['center'],geometry['axis'])
  top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));activate(top);assert top.ForceRebuild3(False);assert bridge.model_issues(sw,top)==(0,0,[]) and not original(top);assert top.Save3(13,e,q) and not e.value
 raise
finally:bridge.interference_issues=original
