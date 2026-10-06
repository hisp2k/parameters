from pathlib import Path
import json
import win32com.client as win32

ROOT = Path(r'C:\Users\adm\Desktop\РАЗРАБОТКА')
OUT = Path('work/sw_audit.json')
sw = win32.GetActiveObject('SldWorks.Application')
asm_path = next(ROOT.rglob("PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM"))

def open_doc(path, kind):
    spec = sw.GetOpenDocSpec(str(path))
    spec.DocumentType = kind
    spec.ReadOnly = True
    spec.Silent = True
    return sw.OpenDoc7(spec)

def safe(obj, name, *args):
    try:
        value = getattr(obj, name)
        return value(*args) if args else value
    except Exception as exc:
        return {'error': str(exc)[:180]}

def features(doc, limit=500):
    out = []
    feat = safe(doc, 'FirstFeature')
    seen = set()
    while feat and len(out) < limit:
        name = safe(feat, 'Name')
        if name in seen:
            break
        seen.add(name)
        out.append({'name': name, 'type': safe(feat, 'GetTypeName2'), 'suppressed': safe(feat, 'IsSuppressed2', 0, None)})
        feat = safe(feat, 'GetNextFeature')
        if isinstance(feat, dict):
            break
    return out

def configs(doc):
    result = safe(doc, 'GetConfigurationNames')
    return list(result) if isinstance(result, (list, tuple)) else result

def equations(doc):
    mgr = safe(doc, 'GetEquationMgr')
    if isinstance(mgr, dict):
        return mgr
    count = safe(mgr, 'GetCount')
    if not isinstance(count, int):
        return {'count': count}
    return {'count': count, 'items': [safe(mgr, 'Equation', i) for i in range(count)]}

doc = open_doc(asm_path, 2)
assembly = {'path': str(asm_path), 'configurations': configs(doc), 'equations': equations(doc), 'features': features(doc)}
ass = safe(doc, 'GetSpecificFeature2')
try:
    doc.ResolveAllLightWeightComponents(True)
except Exception:
    pass
components = []
for comp in doc.GetComponents(False) or []:
    components.append({
        'name': safe(comp, 'Name2'),
        'path': safe(comp, 'GetPathName'),
        'configuration': safe(comp, 'ReferencedConfiguration'),
        'suppression': safe(comp, 'GetSuppression'),
    })
assembly['components'] = components

detail_paths = [p for p in asm_path.parent.rglob('*') if p.suffix.upper() in {'.SLDASM', '.SLDPRT'}]
details = []
for path in detail_paths:
    if path == asm_path:
        continue
    kind = 2 if path.suffix.upper() == '.SLDASM' else 1
    item = {'path': str(path)}
    try:
        subdoc = open_doc(path, kind)
        item['configurations'] = configs(subdoc)
        item['equations'] = equations(subdoc)
        item['features'] = features(subdoc)
    except Exception as exc:
        item['error'] = str(exc)
    details.append(item)

OUT.write_text(json.dumps({'assembly': assembly, 'details': details}, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(json.dumps({'components': len(components), 'details': len(details), 'output': str(OUT)}, ensure_ascii=False))
