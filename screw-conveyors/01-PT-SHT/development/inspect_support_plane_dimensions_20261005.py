from pathlib import Path
import sys,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');d=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
f=d.FirstFeature
while f:
 if f.GetTypeName2=='RefPlane':
  dd=f.GetFirstDisplayDimension
  while dd:
   v=dd.GetDimension2(0);print(v.FullName,v.SystemValue,flush=True);dd=dd.GetNext5
 f=f.GetNextFeature
