from pathlib import Path
import win32com.client as win32

base=(Path('outputs')/'Шнек 1 — параметрическая модель'/'CAD').resolve()
files={
    'tube': next(base.rglob("PT.SHT.01.21.00.09 'Труба шнека'.SLDPRT")),
    'screw': next(base.rglob("PT.SHT.01.24.00.05 'Винт шнека'.SLDPRT")),
}
sw=win32.DispatchEx('SldWorks.Application')
sw.Visible=False
try:
    for key,path in files.items():
        spec=sw.GetOpenDocSpec(str(path))
        spec.DocumentType=1
        spec.ReadOnly=True
        spec.Silent=True
        doc=sw.OpenDoc7(spec)
        print(key, doc.GetPartBox(True))
finally:
    sw.ExitApp()
