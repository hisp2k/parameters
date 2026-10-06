import json
from pathlib import Path
import pythoncom
import win32com.client

pythoncom.CoInitialize()
root = Path.cwd() / 'work' / 'pt-sht-10-working-copy' / 'Модель'
asm = next(root.glob('*Бункер в сборе.SLDASM'))
sw = win32com.client.Dispatch('SldWorks.Application')
print('revision', sw.RevisionNumber)
print('visible', sw.Visible)
errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
doc = sw.OpenDoc6(str(asm), 2, 64, '', errors, warnings)
print('open status', errors.value, warnings.value)
print('opened', bool(doc))
if not doc:
    raise SystemExit(1)
print('title', doc.GetTitle)
print('path', doc.GetPathName)
print('configuration', doc.ConfigurationManager.ActiveConfiguration.Name)
try:
    print('assembly box', doc.GetBox(0))
except Exception as exc:
    print('assembly box error', exc)
assy = doc
try:
    print('resolve', assy.ResolveAllLightWeightComponents(True))
except Exception as exc:
    print('resolve error', exc)
rows = []
for comp in assy.GetComponents(False) or []:
    row = {}
    for key, method in [('name','Name2'), ('path','GetPathName'), ('config','ReferencedConfiguration'), ('suppression','GetSuppression')]:
        try:
            obj = getattr(comp, method)
            row[key] = obj() if callable(obj) else obj
        except Exception as exc:
            row[key] = 'ERROR ' + str(exc)
    try:
        row['box'] = list(comp.GetBox(False, False))
    except Exception as exc:
        row['box'] = 'ERROR ' + str(exc)
    try:
        row['transform'] = list(comp.Transform2.ArrayData)
    except Exception as exc:
        row['transform'] = 'ERROR ' + str(exc)
    rows.append(row)
print(json.dumps(rows, ensure_ascii=False, indent=2))
