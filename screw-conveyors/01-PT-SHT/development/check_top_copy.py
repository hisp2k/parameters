from pathlib import Path
from collections import Counter
import json
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
base = (Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD').resolve()
path = base / "PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM"
spec = sw.GetOpenDocSpec(str(path))
spec.DocumentType = 2
spec.ReadOnly = True
spec.Silent = True
doc = sw.OpenDoc7(spec)
components = doc.GetComponents(False) or []
paths = [Path(c.GetPathName) for c in components]
result = {
    'path': str(path),
    'components': len(components),
    'local_in_copy': sum(str(p).lower().startswith(str(base).lower()) for p in paths),
    'missing': sum(not p.exists() for p in paths),
    'external_existing': sum(p.exists() and not str(p).lower().startswith(str(base).lower()) for p in paths),
    'missing_paths': [{"count": count, "path": str(p)} for p, count in Counter(p for p in paths if not p.exists()).most_common()],
}
Path('work/check_top_copy.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ('components','local_in_copy','missing','external_existing')}, ensure_ascii=False))
