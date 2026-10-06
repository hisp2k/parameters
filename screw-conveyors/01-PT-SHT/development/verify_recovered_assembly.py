"""Open the distinct recovered top assembly and verify component loading."""
from collections import Counter
from pathlib import Path
import json
import sys

import win32com.client as win32

project = Path(sys.argv[1]).resolve()
path = Path(json.loads((project / 'recovered_assembly_check.json').read_text(encoding='utf-8'))['assembly'])
sw = win32.GetActiveObject('SldWorks.Application')
spec = sw.GetOpenDocSpec(str(path))
spec.DocumentType = 2
spec.Silent = True
spec.ReadOnly = True
doc = sw.OpenDoc7(spec)
print('OPEN', bool(doc), 'ERROR', spec.Error, 'WARNING', spec.Warning, flush=True)
if doc is None or Path(doc.GetPathName).resolve() != path.resolve():
    raise RuntimeError('Recovered top assembly failed to open at exact path')
components = doc.GetComponents(False) or []
missing = Counter(c.GetPathName for c in components if c.GetPathName and not Path(c.GetPathName).is_file())
suppressed = Counter(int(c.GetSuppression) for c in components)
recovered = [c.GetPathName for c in components if 'Восстановленные из STEP' in c.GetPathName]
print('COMPONENTS', len(components), 'UNRESOLVED', sum(missing.values()), 'RECOVERED_OCCURRENCES', len(recovered), flush=True)
print('SUPPRESSION_STATES', dict(suppressed), flush=True)
for name, count in missing.items():
    print('MISSING', count, name, flush=True)
report = {'assembly': str(path), 'component_count': len(components),
          'unresolved_count': sum(missing.values()), 'unresolved_paths': dict(missing),
          'recovered_occurrences': len(recovered), 'suppression_states': dict(suppressed),
          'load_error': int(spec.Error), 'load_warning': int(spec.Warning)}
(project / 'recovered_open_check.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
