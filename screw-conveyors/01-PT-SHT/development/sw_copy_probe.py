from pathlib import Path
import json
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
base = Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD'
result = {}
for pattern in ["PT.SHT.01.21.00.00 СБ 'Труба в сборе'.SLDASM", "PT.SHT.01.24.00.00 СБ 'Шнековый вал'.SLDASM"]:
    p = next(base.rglob(pattern)).resolve()
    spec = sw.GetOpenDocSpec(str(p))
    spec.DocumentType = 2
    spec.ReadOnly = False
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
    mgr = doc.GetEquationMgr
    comps = doc.GetComponents(False)
    result[p.name] = {
        'actual_path': doc.GetPathName,
        'equations': [mgr.Equation(i) for i in range(mgr.GetCount)],
        'component_paths': sorted(set(c.GetPathName for c in comps)),
        'save_flag': doc.GetSaveFlag,
    }
Path('work/sw_copy_probe.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('done')
