import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
sw = win32.Dispatch('SldWorks.Application')
target = r'C:\Users\adm\Documents\Codex\2026-09-29\c-users-adm-desktop-01-pt\work\pt-sht-10-210l\Модель\PT-SHT-10-210L.SLDASM'
assert target.lower() in sw.ActiveDoc.GetPathName.lower()
rot = pythoncom.GetRunningObjectTable()
ctx = pythoncom.CreateBindCtx(0)
en = rot.EnumRunning()
moniker = None
expected = str(sw.GetProcessID) + 'EFDApiLibROT'
while True:
    item = en.Next(1)
    if not item:
        break
    if item[0].GetDisplayName(ctx, None) == expected:
        moniker = item[0]
        break
assert moniker, expected
lib = pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
types = {lib.GetDocumentation(i)[0]: lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount())}
def typed(obj, name):
    return win32.dynamic.Dispatch(obj._oleobj_ if hasattr(obj,'_oleobj_') else obj, typeinfo=types[name])
app = typed(rot.GetObject(moniker).QueryInterface(pythoncom.IID_IDispatch), 'IApplication')
doc = typed(app.GetActiveDoc(), 'IDocument')
old = typed(doc.GetActiveProject(), 'IProject')
print('OLD',old.GetName(),flush=True)
existing = []
try:
    existing = [typed(x,'IProject').GetName() for x in doc.GetProjects1() or []]
except Exception as exc:
    print('LIST ERROR',repr(exc),flush=True)
if 'PT-SHT-10-210L-Q10-closed' in existing:
    print('ALREADY',existing,flush=True)
else:
    new = typed(doc.CreateProject(None), 'IProject')
    print('NEW TEMPLATE',new.GetName(),flush=True)
    new.SetName('PT-SHT-10-210L-Q10-closed')
    print('ADD',doc.AddProject(new,'По умолчанию'),flush=True)
    print('ACTIVE',typed(doc.GetActiveProject(),'IProject').GetName(),flush=True)
