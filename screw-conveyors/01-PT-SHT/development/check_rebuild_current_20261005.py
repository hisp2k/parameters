"""Repeat native assembly rebuild checks and retain every rollback result."""
from pathlib import Path
from datetime import datetime
import sys, json, copy
import pythoncom, win32com.client as w
from native_ear_saddle import saddle_surfaces

base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import bridge

original=json.loads(bridge.STATE.read_text(encoding='utf-8'))
try:
    sw=w.GetActiveObject('SldWorks.Application')
except pythoncom.com_error:
    sw=w.Dispatch('SldWorks.Application');sw.Visible=True
bridge.open_models(sw)
stamp=datetime.now().strftime('%Y%m%d-%H%M%S')
output=base/f'geometry_rebuild_{stamp}.json'
rows=[]

def ears():
    tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
    return [{'component':c.Name2,'saddle_diameters_mm':[s[6]*2000 for s in saddle_surfaces(c.GetModelDoc2)]}
            for c in tube.GetComponents(True) if 'Ухо' in c.Name2]

def persist():
    output.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    (base/'geometry_rebuild_latest.json').write_text(output.read_text(encoding='utf-8'),encoding='utf-8')

print('Verify the saved baseline with a full assembly rebuild',flush=True)
baseline=bridge.apply(original['values'],sw,original['selection'],original['design_mode'])
assert baseline['ok'],baseline
print('Baseline verified:',baseline['cad_verification'],flush=True)

for parameter,value in [('working_length',original['values']['working_length']+100),
                        ('tube_diameter',original['values']['tube_diameter']+4),('incline',50)]:
    row={'parameter':parameter,'before':original['values'][parameter],'tested':value,
         'checked_at':datetime.now().astimezone().isoformat(timespec='seconds')}
    request=copy.deepcopy(original['values']);request[parameter]=value
    selection=copy.deepcopy(original['selection'])
    if parameter=='tube_diameter':selection['tube']='custom'
    print('TEST',parameter,request[parameter],flush=True)
    try:
        result=bridge.apply(request,sw,selection,original['design_mode'])
        assert result['ok'],result
        row.update(applied=True,verification=result['cad_verification'],snapshot=result['snapshot'],
                   saddle_geometry=ears())
        assert len(row['saddle_geometry'])==4
        assert all(r['saddle_diameters_mm'] and
                   all(abs(d-request['tube_diameter'])<1e-6 for d in r['saddle_diameters_mm'])
                   for r in row['saddle_geometry'])
        print('PASS',parameter,'real geometry checked; model errors and interferences 0',flush=True)
    except Exception as exc:
        row.update(applied=False,errors=[str(exc)])
        print('REJECTED',parameter,str(exc),flush=True)
    finally:
        print('RESTORE',parameter,'to the saved baseline',flush=True)
        result=bridge.apply(original['values'],sw,original['selection'],original['design_mode'])
        assert result['ok'],result
        row['restored_verification']=result['cad_verification']
        row['restored_geometry']=result['cad_verification']['measured_geometry']
        row['restored_saddle_geometry']=ears()
        assert all(r['saddle_diameters_mm'] and all(abs(d-original['values']['tube_diameter'])<1e-6
                   for d in r['saddle_diameters_mm']) for r in row['restored_saddle_geometry'])
        rows.append(row);persist()
        print('RESTORED',parameter,'all native checks 0',flush=True)
print('All rebuild checks finished:',output,flush=True)
