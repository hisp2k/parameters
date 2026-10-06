import win32com.client as win32
import pythoncom
from pathlib import Path

sw = win32.GetActiveObject('SldWorks.Application')
path = (Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD' / "PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM").resolve()
doc = sw.GetOpenDocumentByName(str(path))
print('doc', bool(doc))
print('active', sw.ActiveDoc.GetPathName if sw.ActiveDoc else None)
print('documents', [x.GetPathName for x in (sw.GetDocuments or [])])
if not doc:
    spec = sw.GetOpenDocSpec(str(path))
    spec.DocumentType = 2
    spec.ReadOnly = True
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
    print('opened', bool(doc), 'error', spec.Error, 'warning', spec.Warning)
if doc:
    print('title', doc.GetTitle)
    try:
        print('activate3', sw.ActivateDoc3(doc.GetTitle, False, 1, 0))
    except Exception as exc:
        print('activate3_error', type(exc).__name__, str(exc)[:300])
    try:
        print('activate2', sw.ActivateDoc2(doc.GetTitle, False, 0))
    except Exception as exc:
        print('activate2_error', type(exc).__name__, str(exc)[:300])
    try:
        errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        print('activate2_ref', sw.ActivateDoc2(doc.GetTitle, False, errors), errors.value)
    except Exception as exc:
        print('activate2_ref_error', type(exc).__name__, str(exc)[:300])
