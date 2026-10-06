from pathlib import Path
import sys,json,copy
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
state=json.loads(bridge.STATE.read_text(encoding='utf-8'));before=bridge.STATE.read_bytes();rows=[]
for label,changes,mode in [('too_short',{'working_length':2000},'special'),('diameter_overlap',{'tube_diameter':130},'special'),('vertical_angle',{'incline':90},'special'),('gost_angle_limit',{'incline':55},'gost')]:
 values=copy.deepcopy(state['values']);values.update(changes)
 result=bridge.apply(values,sw=object(),selection=state['selection'],design_mode=mode)
 assert not result['ok'] and result['errors'],result
 assert bridge.STATE.read_bytes()==before
 rows.append({'case':label,'changes':changes,'design_mode':mode,'rejected_before_cad':True,'errors':result['errors']})
(base/'geometry_preflight_20261005.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('4 invalid cases rejected before any CAD access; state unchanged')
