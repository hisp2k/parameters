from pathlib import Path
import win32com.client as win32

root = Path('outputs') / 'Шнек 1 — параметрическая модель' / 'Чертежи'
batch = sorted(path for path in root.iterdir() if path.is_dir())[-1]
path = batch / 'Сборка шнека.SLDDRW'
sw = win32.GetActiveObject('SldWorks.Application')
spec = sw.GetOpenDocSpec(str(path.resolve()))
spec.DocumentType = 3
spec.ReadOnly = True
spec.Silent = True
doc = sw.OpenDoc7(spec)
print('open', bool(doc), spec.Error)
if doc:
    doc.ViewZoomtofit2()
    out = Path('work/drawing_preview.png').resolve()
    print('export', doc.SaveAs3(str(out), 0, 2), out.exists(), out.stat().st_size if out.exists() else 0)
