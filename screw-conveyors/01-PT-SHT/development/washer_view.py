from pathlib import Path
import sys
import pythoncom
import win32com.client as win32

project = Path(sys.argv[1])
part = next((project / 'CAD').glob('Шайба пружинная М8 DIN127 А2.SLDPRT'))
output = Path(sys.argv[2]).resolve()
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(part))
if doc is None:
    spec = sw.GetOpenDocSpec(str(part))
    spec.DocumentType = 1
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
if doc is None:
    raise RuntimeError('Не удалось открыть шайбу')
errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc2(doc.GetTitle, False, errors)
doc.ShowNamedView2('*Isometric', 7)
doc.ViewZoomtofit2()
result = doc.SaveAs3(str(output), 0, 2)
print('OUTPUT', output, 'RESULT', result, 'SIZE', output.stat().st_size if output.exists() else 0)
