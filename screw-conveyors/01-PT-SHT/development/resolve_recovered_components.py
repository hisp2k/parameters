"""Attempt to resolve saved suppressed components in the recovered assembly."""
from pathlib import Path
import json
import sys

import pythoncom
import win32com.client as win32

project = Path(sys.argv[1]).resolve()
path = Path(json.loads((project / 'recovered_assembly_check.json').read_text(encoding='utf-8'))['assembly'])
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(path))
if doc is None or doc.IsOpenedReadOnly:
    raise RuntimeError('Recovered assembly must be open for editing')
error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(doc.GetTitle, False, error)
if error.value:
    raise RuntimeError(f'Activate error {error.value}')

names = [c.Name2 for c in doc.GetComponents(False) or [] if int(c.GetSuppression) == 0]
names.sort(key=lambda value: value.count('/'))
results = []
for name in names:
    current = next((c for c in doc.GetComponents(False) or [] if c.Name2 == name), None)
    if current is None:
        results.append({'name': name, 'status': 'disappeared'})
        continue
    if int(current.GetSuppression) != 0:
        results.append({'name': name, 'status': 'already_resolved'})
        continue
    if not Path(current.GetPathName).is_file():
        results.append({'name': name, 'status': 'missing_file'})
        continue
    code = int(current.SetSuppression2(2))
    state = int(current.GetSuppression)
    result = {'name': name, 'code': code, 'state': state,
              'status': 'resolved' if state in (2, 3) else 'still_suppressed'}
    results.append(result)
    print(result['status'], code, name, flush=True)
    (project / 'recovered_resolve_attempt.json').write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

states = {}
for component in doc.GetComponents(False) or []:
    state = int(component.GetSuppression)
    states[state] = states.get(state, 0) + 1
print('FINAL_STATES', states, flush=True)
print('ATTEMPTS', len(results), 'RESOLVED', sum(r['status'] == 'resolved' for r in results), flush=True)
