from pathlib import Path
from collections import Counter
import json
import win32com.client as win32

base = (Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD').resolve()
assembly_path = base / "PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM"
sw = win32.GetActiveObject('SldWorks.Application')
spec = sw.GetOpenDocSpec(str(assembly_path))
spec.DocumentType = 2
spec.ReadOnly = True
spec.Silent = True
doc = sw.OpenDoc7(spec)
if doc is None:
    raise RuntimeError('SolidWorks не открыл главную сборку')

def get(obj, attr):
    try:
        v = getattr(obj, attr)
        return v() if callable(v) else v
    except Exception as e:
        return {'error': str(e)[:120]}

rows = []
for comp in doc.GetComponents(False) or []:
    raw_path = get(comp, 'GetPathName')
    path = Path(raw_path) if isinstance(raw_path, str) and raw_path else None
    rows.append({
        'name': get(comp, 'Name2'),
        'path': raw_path,
        'exists': bool(path and path.exists()),
        'local': bool(path and str(path).lower().startswith(str(base).lower())),
        'suppression': get(comp, 'GetSuppression'),
        'visible': get(comp, 'Visible'),
        'is_hidden': get(comp, 'IsHidden'),
        'configuration': get(comp, 'ReferencedConfiguration'),
    })

result = {
    'assembly': str(assembly_path),
    'configuration': get(doc, 'ConfigurationManager.ActiveConfiguration.Name'),
    'component_count': len(rows),
    'exists_count': sum(x['exists'] for x in rows),
    'missing_count': sum(not x['exists'] for x in rows),
    'local_count': sum(x['local'] for x in rows),
    'suppression_counts': dict(Counter(str(x['suppression']) for x in rows)),
    'visibility_counts': dict(Counter(str(x['visible']) for x in rows)),
    'hidden_counts': dict(Counter(str(x['is_hidden']) for x in rows)),
    'missing_paths': [{'name': k, 'count': v} for k, v in Counter(Path(x['path']).stem for x in rows if not x['exists'] and isinstance(x['path'], str)).most_common()],
    'components': rows,
}
Path('work/audit_current_assembly.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({k: result[k] for k in ('component_count','exists_count','missing_count','local_count','suppression_counts','visibility_counts','hidden_counts')}, ensure_ascii=True))
