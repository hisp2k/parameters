from pathlib import Path
import win32com.client as w
sw=w.GetActiveObject('SldWorks.Application')
base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
path=base/'CAD_восстановленный'/"PT.SHT.01.20.00.00 СБ 'Шнек 1' — восстановлено.SLDASM"
d=sw.GetOpenDocumentByName(str(path))
print('top open',d is not None,'dirty',d.GetSaveFlag if d else None,flush=True)
if d:
 for c in d.GetComponents(True):
  if 'Обойма нижняя' in c.GetPathName:print(c.Name2,c.GetPathName,'fixed',c.IsFixed,'transform',list(c.Transform2.ArrayData),flush=True)
