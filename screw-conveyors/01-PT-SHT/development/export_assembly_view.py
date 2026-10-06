from pathlib import Path
import win32com.client as win32

path = (Path('outputs') / 'Шнек 1 — параметрическая модель' / 'CAD' / "PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM").resolve()
out = Path('work/assembly_view.png').resolve()
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(path))
print('document', bool(doc))
print('active', sw.ActiveDoc.GetTitle if sw.ActiveDoc else None)
if doc:
    doc.ViewZoomtofit2()
    print('save_png', doc.SaveAs3(str(out), 0, 2))
    print('image', out.exists(), out.stat().st_size if out.exists() else 0)
