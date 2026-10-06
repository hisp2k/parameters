from pathlib import Path
from datetime import datetime
import json,sys,copy
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge,journal,server
sw=w.GetActiveObject('SldWorks.Application');initial=json.loads(bridge.STATE.read_text(encoding='utf-8'))
assert initial['values']['incline']==55 and initial['values']['tube_diameter']==133
path=base/'geometry_rebuild_latest.json';archive=base/'geometry_rebuild_before_dependency_repair_20261005.json'
if not archive.exists():archive.write_bytes(path.read_bytes())
rows=[]
try:
 for key,tested in [('working_length',2610),('tube_diameter',141),('incline',35)]:
  values=copy.deepcopy(initial['values']);values[key]=tested
  row={'parameter':key,'before':initial['values'][key],'tested':tested,'checked_at':datetime.now().astimezone().isoformat(timespec='seconds')}
  try:
   previous=json.loads(bridge.STATE.read_text(encoding='utf-8'))
   result=bridge.apply(values,sw,initial['selection'],initial['design_mode'])
   journal.record_apply(previous,result)
   row.update(applied=result['ok'],verification=result['cad_verification'],snapshot=result['snapshot'])
   print('Verified changed parameter',key,tested,result['cad_verification'],flush=True)
  except Exception as exc:
   row.update(applied=False,errors=[str(exc)],details=getattr(exc,'details',{}))
   print('Rejected changed parameter',key,str(exc),flush=True)
  finally:
   previous=json.loads(bridge.STATE.read_text(encoding='utf-8'))
   restored=bridge.apply(initial['values'],sw,initial['selection'],initial['design_mode'])
   journal.record_apply(previous,restored)
   row.update(restored_geometry=restored['cad_verification']['measured_geometry'],restored_verification=restored['cad_verification'])
   rows.append(row);path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
   print('Restored saved user parameters after',key,flush=True)
 finally_result=json.loads(bridge.STATE.read_text(encoding='utf-8'))
 server.save_apply_outcome({'values':initial['values'],'selection':initial['selection'],'design_mode':initial['design_mode']},{'ok':True,**finally_result})
finally:
 print('Roundtrip proof',str(path),flush=True)
