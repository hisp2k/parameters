"""Check the actual assembly through the public bridge, then restore its diameter."""
from pathlib import Path
import sys, json, copy
import win32com.client as w
from native_ear_saddle import saddle_surfaces

base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import bridge
sw=w.GetActiveObject('SldWorks.Application')
original=json.loads(bridge.STATE.read_text(encoding='utf-8'))
assert original['values']['tube_diameter']==141
row={'parameter':'tube_diameter','before':141,'tested':145}
output=base/'geometry_native_ear_20261005.json'

def measured_saddles():
    tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
    ears=[c for c in tube.GetComponents(True) if 'Ухо' in c.Name2]
    assert len(ears)==4
    return [{'component':c.Name2,'diameters_mm':[s[6]*2000 for s in saddle_surfaces(c.GetModelDoc2)]}
            for c in ears]

try:
    values=copy.deepcopy(original['values']);values['tube_diameter']=145
    selection=copy.deepcopy(original['selection']);selection['tube']='custom'
    print('Apply diameter 145 through the public bridge',flush=True)
    result=bridge.apply(values,sw,selection,original['design_mode'])
    assert result['ok'],result
    row.update(applied=True,verification=result['cad_verification'],snapshot=result['snapshot'],
               saddle_geometry=measured_saddles())
    assert all(r['diameters_mm'] and all(abs(x-145)<1e-6 for x in r['diameters_mm'])
               for r in row['saddle_geometry'])
    print('Diameter 145: all four saddles follow, native model errors and interferences zero',flush=True)
except Exception as exc:
    row.update(applied=False,errors=[str(exc)])
    print('Diameter 145 rejected:',str(exc),flush=True)
finally:
    print('Restore diameter 141 and recheck through the public bridge',flush=True)
    result=bridge.apply(original['values'],sw,original['selection'],original['design_mode'])
    assert result['ok'],result
    row['restored_verification']=result['cad_verification']
    row['restored_geometry']=result['cad_verification']['measured_geometry']
    row['restored_saddle_geometry']=measured_saddles()
    assert all(r['diameters_mm'] and all(abs(x-141)<1e-6 for x in r['diameters_mm'])
               for r in row['restored_saddle_geometry'])
    output.write_text(json.dumps([row],ensure_ascii=False,indent=2),encoding='utf-8')
    print('Diameter 141 restored, native checks zero; proof:',output,flush=True)
