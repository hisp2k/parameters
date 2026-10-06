from pathlib import Path
import win32com.client as win32
import pythoncom

sw=win32.GetActiveObject('SldWorks.Application')
base=(Path('outputs')/'Шнек 1 — параметрическая модель'/'CAD').resolve()
part=next(base.rglob("PT.SHT.01.21.00.09 'Труба шнека'.SLDPRT"))
asm=next(base.rglob("PT.SHT.01.21.00.00 СБ 'Труба в сборе'.SLDASM"))
for d in sw.GetDocuments or []:
    if d.GetPathName.lower()==str(part).lower() and d.IsOpenedReadOnly:
        sw.CloseDoc(d.GetTitle)
spec=sw.GetOpenDocSpec(str(asm))
spec.DocumentType=2
spec.ReadOnly=False
spec.Silent=True
doc=sw.OpenDoc7(spec)
error=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
sw.ActivateDoc2(doc.GetTitle,False,error)
print('activate_error',error.value)
print('eq',[(i,doc.GetEquationMgr.Equation(i).encode('unicode_escape').decode()) for i in range(doc.GetEquationMgr.GetCount) if 'Диаметр трубы' in doc.GetEquationMgr.Equation(i)])
print('rebuild',doc.ForceRebuild3(False))
for d in sw.GetDocuments or []:
    if d.GetPathName.lower()==str(part).lower():
        print('part_readonly',d.IsOpenedReadOnly,'saveflag',d.GetSaveFlag,'box',d.GetPartBox(True))
