from pathlib import Path
import sys,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');d=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
f=d.FirstFeature
while f:
 typ=f.GetTypeName2
 print('F',f.Name,typ,flush=True)
 if typ in ('ProfileFeature','3DProfileFeature'):
  sk=f.GetSpecificFeature2
  for segment in sk.GetSketchSegments or []:
   print('SEG',segment.GetType,flush=True)
  di=f.GetFirstDisplayDimension
  while di:
   dim=di.GetDimension2(0);print('DIM',dim.FullName,dim.SystemValue,flush=True);di=di.GetNext5
 if typ=='RefAxis':
  definition=f.GetDefinition
  print('AXIS',f.GetSpecificFeature2.GetRefAxisParams,'definition',definition,flush=True)
 f=f.GetNextFeature
