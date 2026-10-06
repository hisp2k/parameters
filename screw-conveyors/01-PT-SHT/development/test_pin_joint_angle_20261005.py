from pathlib import Path
import sys,json,copy
from datetime import datetime
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge
sw=w.GetActiveObject('SldWorks.Application')
original=json.loads(bridge.STATE.read_text(encoding='utf-8'))
proof={'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),'checks':[]}
try:
    for angle in [35,original['values']['incline']]:
        values=copy.deepcopy(original['values']);values['incline']=angle
        print('Apply and verify angle',angle,flush=True)
        result=bridge.apply(values,sw,original['selection'],original['design_mode'])
        assert result['ok'],result
        proof['checks'].append({'angle':angle,'verification':result['cad_verification'],'snapshot':result['snapshot']})
        (base/'pin_joint_angle_test_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
        print('Saved verified angle',angle,flush=True)
finally:
    current=json.loads(bridge.STATE.read_text(encoding='utf-8'))
    if current['values']!=original['values']:
        result=bridge.apply(original['values'],sw,original['selection'],original['design_mode']);assert result['ok'],result
        print('Restored original values',flush=True)
