from pathlib import Path
import pythoncom
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
cad = str((Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD').resolve()).lower()
for doc in sw.GetDocuments or []:
    path = doc.GetPathName
    if not path.lower().startswith(cad) or not doc.GetSaveFlag:
        continue
    err = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warn = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    ok = doc.Save3(1, err, warn)
    print(Path(path).name.encode('unicode_escape').decode(), bool(ok), err.value, warn.value)
