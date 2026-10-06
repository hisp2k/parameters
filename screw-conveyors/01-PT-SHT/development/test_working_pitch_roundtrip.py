from pathlib import Path
import sys,json,copy,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');original=json.loads(bridge.STATE.read_text(encoding='utf-8'));rows=[]
try:
 for pitch in [100,105]:
  v=copy.deepcopy(original['values']);v['pitch']=pitch
  r=bridge.apply(v,sw,original['selection'],original['design_mode']);assert r['ok'],r
  top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));part=next(c.GetModelDoc2 for c in top.GetComponents(False) if 'Винт шнека' in c.Name2)
  actual=part.Parameter('D4@Спираль1').SystemValue*1000;assert abs(actual-pitch)<1e-7,(actual,pitch)
  rows.append({'pitch_mm':pitch,'native_helix_pitch_mm':actual,'rebuilds':r['rebuilds'],'ok':True});print('pitch roundtrip',pitch,'OK',flush=True)
 v=copy.deepcopy(original['values']);v['turns']=26;r=bridge.apply(v,sw,original['selection'],original['design_mode']);assert not r['ok'];rows.append({'invalid_turns':26,'rejected':True,'errors':r['errors']});print('26 turns rejected',flush=True)
finally:
 current=json.loads(bridge.STATE.read_text(encoding='utf-8'))
 if current['values']!=original['values']:bridge.apply(original['values'],sw,original['selection'],original['design_mode'])
(base/'parameter_roundtrip_20261004.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
