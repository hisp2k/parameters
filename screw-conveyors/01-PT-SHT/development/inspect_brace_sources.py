from pathlib import Path
import sys,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');support=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
for c in support.GetComponents(True):
 if 'Подкос' in c.Name2:
  p=c.GetModelDoc2;print(c.Name2,p.GetPathName)
  f=p.FirstFeature
  while f:
   print(f.Name,f.GetTypeName2);f=f.GetNextFeature
  print('Dependencies',p.Extension.GetDependencies(False,False,False,False,False))
