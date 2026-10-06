from pathlib import Path
import win32com.client as c

sw = c.GetActiveObject('SldWorks.Application')
root = Path(r'C:\Users\adm\Desktop\РАЗРАБОТКА')
path = next(root.rglob("PT.SHT.01.20.00.00 СБ 'Шнек 1'.SLDASM"))
print('path:', path, flush=True)
spec = sw.GetOpenDocSpec(str(path))
spec.DocumentType = 2
spec.ReadOnly = True
spec.Silent = True
opened = sw.OpenDoc7(spec)
print('opened:', type(opened), str(opened)[:100], flush=True)
model = sw.ActiveDoc
print('active title:', model.GetTitle, flush=True)
print('active path:', model.GetPathName, flush=True)
