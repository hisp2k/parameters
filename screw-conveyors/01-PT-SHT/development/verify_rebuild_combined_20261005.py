from pathlib import Path
from datetime import datetime
import json,sys,copy
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge,journal,server
sw=w.GetActiveObject('SldWorks.Application');initial=json.loads(bridge.STATE.read_text(encoding='utf-8'));assert initial['values']['incline']==55
path=base/'geometry_rebuild_latest.json';archive=base/'geometry_rebuild_before_brace_transition_20261005.json'
if not archive.exists():archive.write_bytes(path.read_bytes())
values=copy.deepcopy(initial['values']);changes={'working_length':2610,'tube_diameter':141,'incline':35};values.update(changes)
rows=[{'parameter':key,'before':initial['values'][key],'tested':value,'simultaneous':True,'checked_at':datetime.now().astimezone().isoformat(timespec='seconds'),'test_values':values} for key,value in changes.items()]
try:
 previous=json.loads(bridge.STATE.read_text(encoding='utf-8'));result=bridge.apply(values,sw,initial['selection'],initial['design_mode']);journal.record_apply(previous,result)
 for row in rows:row.update(applied=True,verification=result['cad_verification'],snapshot=result['snapshot'])
 print('Joint length / diameter / angle passed',result['cad_verification'],flush=True)
except Exception as exc:
 for row in rows:row.update(applied=False,errors=[str(exc)],details=getattr(exc,'details',{}))
 print('Joint test failed',str(exc),flush=True)
finally:
 previous=json.loads(bridge.STATE.read_text(encoding='utf-8'));restored=bridge.apply(initial['values'],sw,initial['selection'],initial['design_mode']);journal.record_apply(previous,restored)
 for row in rows:row.update(restored_geometry=restored['cad_verification']['measured_geometry'],restored_verification=restored['cad_verification'])
 path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');server.save_apply_outcome(initial,restored)
 print('User parameters restored and saved',restored['cad_verification'],flush=True)
assert all(row['applied'] for row in rows),rows
