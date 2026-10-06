from pathlib import Path
import sys,json,copy,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');original=json.loads(bridge.STATE.read_text(encoding='utf-8'));rows=[]
try:
 for length in [2610,2510]:
  values=copy.deepcopy(original['values']);values['working_length']=length
  r=bridge.apply(values,sw,original['selection'],original['design_mode']);assert r['ok'],r
  rows.append({'working_length':length,'ok':True,'verification':r['cad_verification'],'rebuilt_nodes':r['rebuilt_nodes'],'snapshot':r['snapshot']})
  (base/'geometry_final_length_20261005.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
  print('final length',length,'verified',r['cad_verification']['measured_geometry'],flush=True)
finally:
 if json.loads(bridge.STATE.read_text(encoding='utf-8'))['values']!=original['values']:
  assert bridge.apply(original['values'],sw,original['selection'],original['design_mode'])['ok']
