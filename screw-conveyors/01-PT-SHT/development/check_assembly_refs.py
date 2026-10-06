from collections import Counter
from pathlib import Path
import sys
import win32com.client as win32

project = Path(sys.argv[1])
assembly = next((project / 'CAD').glob("*20.00.00*Шнек 1*.SLDASM"))
sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.GetOpenDocumentByName(str(assembly))
if doc is None:
    spec = sw.GetOpenDocSpec(str(assembly))
    spec.DocumentType = 2
    spec.Silent = True
    doc = sw.OpenDoc7(spec)
missing = Counter(Path(c.GetPathName).name for c in (doc.GetComponents(False) or [])
                  if c.GetPathName and not Path(c.GetPathName).is_file())
for c in (doc.GetComponents(False) or []):
    if 'Сбрасыватель' in c.GetPathName:
        print('SBROS_REF', c.GetPathName)
for name, count in sorted(missing.items()):
    print(f'{count:3} {name}')
print('TOTAL', sum(missing.values()), 'UNIQUE', len(missing))
if len(sys.argv) > 2:
    supplied = Path(sys.argv[2])
    candidates = {p.name.casefold(): p for p in supplied.rglob('*') if p.is_file()}
    print('FOUND_IN_SUPPLIED', sorted(name for name in missing if name.casefold() in candidates))
