from pathlib import Path
import sys,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');s=sw.GetOpenDocumentByName(str(bridge.FILES['support']))
for c in s.GetComponents(True):
 if 'Подкос' in c.Name2:
  p=c.GetModelDoc2;print(c.Name2,'volume',sum(b.GetMassProperties(1)[3] for b in p.GetBodies2(0,True))*1e9,'bodies',len(p.GetBodies2(0,True)))
top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));print('Geometry',bridge.measured_geometry(top));print('Issues',bridge.model_issues(sw,top))
