from pathlib import Path
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
path = next((Path('work') / 'mate_trial' / 'CAD_восстановленный').glob("PT.SHT.01.20*.SLDASM")).resolve()
for other in sorted(sw.GetDocuments or [], key=lambda item: item.GetType != 2):
    if 'Шнек 1 — параметрическая модель' in other.GetPathName:
        if other.GetSaveFlag:
            raise RuntimeError('Open model has unsaved changes: ' + other.GetTitle)
        sw.CloseDoc(other.GetTitle)
spec = sw.GetOpenDocSpec(str(path))
spec.DocumentType = 2
spec.ReadOnly = False
spec.Silent = True
doc = sw.GetOpenDocumentByName(str(path)) or sw.OpenDoc7(spec)
print('opened', doc is not None, 'error', spec.Error)
if doc:
    parts = doc.GetComponents(False) or []
    print('path', doc.GetPathName)
    print('components', len(parts))
    print('trial paths', sum('mate_trial' in p.GetPathName for p in parts))
    print('missing', sum(not Path(p.GetPathName).exists() for p in parts if p.GetPathName))
    print('save flag', doc.GetSaveFlag)
