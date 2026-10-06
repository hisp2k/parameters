from pathlib import Path
import json
import shutil
import sys
import traceback
import win32com.client as win32

src = (Path('outputs') / 'Шнек 1 — параметрическая модель').resolve()
test = (Path('work') / 'validation_model').resolve()
if test.exists():
    raise SystemExit('Validation target already exists; leaving it untouched')
(test / 'CAD').mkdir(parents=True)
shutil.copytree(src / 'CAD' / 'Шнек', test / 'CAD' / 'Шнек', ignore=shutil.ignore_patterns('~$*'))
shutil.copy2(src / 'state.json', test / 'state.json')
sys.path.insert(0, str(src))
import bridge

bridge.BASE = test
bridge.CAD = test / 'CAD'
bridge.STATE = test / 'state.json'
bridge.FILES = {key: test / 'CAD' / path.relative_to(src / 'CAD') for key, path in bridge.FILES.items()}
base = json.loads(bridge.STATE.read_text(encoding='utf-8'))['values']
body = dict(base)
body.update(working_length=base['working_length']+10, tube_diameter=base['tube_diameter']+3,
            tube_wall=base['tube_wall']+0.5, incline=base['incline']+1,
            inlet_diameter=base['inlet_diameter']+1, inlet_length=base['inlet_length']+5,
            inlet_wall=base['inlet_wall']+0.5)
screw = dict(body)
screw.update(screw_diameter=base['screw_diameter']+0.5, pitch=base['pitch']-1,
             blade_thickness=base['blade_thickness']+0.5,
             shaft_diameter=base['shaft_diameter']+1, shaft_wall=base['shaft_wall']+0.5,
             turns=base['turns']-1)

report = {'baseline': base, 'body_candidate': body, 'screw_candidate': screw, 'checks': []}
sw = win32.DispatchEx('SldWorks.Application')
sw.Visible = False
try:
    for label, values in [('body', body), ('screw', screw)]:
        result = bridge.apply(values, sw=sw)
        report['checks'].append({'scenario': label, 'ok': result['ok'],
                                 'saved_files': len(result.get('saves', {})),
                                 'rebuilds': result.get('rebuilds'),
                                 'save_errors': [x for x in result.get('saves', {}).values() if not x['saved'] or x['errors'] or x['warnings']]})
except Exception as exc:
    report['error'] = repr(exc)
    report['traceback'] = traceback.format_exc()
finally:
    sw.ExitApp()

(Path('work') / 'validation_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'checks': report['checks'], 'error': report.get('error')}, ensure_ascii=False))
