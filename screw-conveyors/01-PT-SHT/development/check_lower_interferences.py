from pathlib import Path
import json
import sys
import pythoncom
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
title = sys.argv[1] if len(sys.argv) > 1 else "PT.SHT.01.23.00.00 СБ 'Обойма нижняя' — восстановлено.SLDASM"
doc = next(d for d in sw.GetDocuments if d.GetTitle == title)
err = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(doc.GetTitle, False, err)
if err.value:
    raise RuntimeError(f'Activation error {err.value}')
mgr = doc.InterferenceDetectionManager
mgr.TreatCoincidenceAsInterference = False
mgr.TreatSubAssembliesAsComponents = False
mgr.IncludeMultibodyPartInterferences = True
mgr.IgnoreHiddenBodies = False
mgr.MakeInterferingPartsTransparent = False
mgr.CreateFastenersFolder = False
print('calculating', doc.GetPathName, flush=True)
try:
    items = mgr.GetInterferences or []
    rows = []
    for item in items:
        rows.append({'components': [c.Name2 for c in item.Components or []],
                     'volume_mm3': float(item.Volume) * 1e9})
    result = {'assembly': doc.GetPathName, 'dirty': bool(doc.GetSaveFlag),
              'count': len(rows), 'interferences': rows}
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('work/lower_interferences_' + ('trial' if 'испытание' in title else 'working') + '.json')
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
finally:
    if callable(mgr.Done):
        mgr.Done()

