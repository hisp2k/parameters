from pathlib import Path
import win32com.client as win32

path = next((Path('work') / 'mate_trial' / 'CAD_восстановленный').glob("PT.SHT.01.20*.SLDASM")).resolve()
print('starting separate SolidWorks', flush=True)
sw = win32.DispatchEx('SldWorks.Application')
sw.Visible = False
print('started', sw.RevisionNumber, flush=True)
spec = sw.GetOpenDocSpec(str(path))
spec.DocumentType = 2
spec.ReadOnly = False
spec.Silent = True
doc = sw.OpenDoc7(spec)
print('opened', doc is not None, 'error', spec.Error, flush=True)
if doc:
    components = doc.GetComponents(False) or []
    print('path', doc.GetPathName, flush=True)
    print('components', len(components), flush=True)
    print('trial paths', sum('mate_trial' in item.GetPathName for item in components), flush=True)
    print('missing', sum(not Path(item.GetPathName).exists() for item in components if item.GetPathName), flush=True)
