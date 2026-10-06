from pathlib import Path
import sys
import win32com.client as win32

project = Path(sys.argv[1])
tube = next((project / 'CAD').rglob("PT.SHT.01.21.00.00 СБ 'Труба в сборе'.SLDASM"))
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(tube))
if doc is None:
    spec = sw.GetOpenDocSpec(str(tube))
    spec.DocumentType = 2
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
print('TUBE', tube, 'LOADED', bool(doc), 'SAVE_FLAG', doc.GetSaveFlag if doc else None)
if doc:
    for component in doc.GetComponents(False) or []:
        if 'Сбрасыватель' in component.GetPathName:
            print('SBROS_REF', component.GetPathName)
            print('SUPPRESSION', component.GetSuppression)
