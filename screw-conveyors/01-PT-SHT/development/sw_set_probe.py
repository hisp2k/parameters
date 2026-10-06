from pathlib import Path
import pythoncom
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
p = next((Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD').rglob("PT.SHT.01.21.00.00 СБ 'Труба в сборе'.SLDASM")).resolve()
doc = next((d for d in (sw.GetDocuments or []) if d.GetPathName.lower() == str(p).lower()), None)
if doc is None:
    spec = sw.GetOpenDocSpec(str(p))
    spec.DocumentType = 2
    spec.ReadOnly = False
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
mgr = doc.GetEquationMgr
old = mgr.Equation(0)
print('old', old.encode('unicode_escape').decode())
try:
    value = mgr.SetEquationAndConfigurationOption(0, old, 2, None)
    print('put', value)
except Exception as e:
    print('put_error', repr(e))
print('new', mgr.Equation(0).encode('unicode_escape').decode())
