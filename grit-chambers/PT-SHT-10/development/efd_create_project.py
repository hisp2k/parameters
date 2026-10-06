import pythoncom
import win32com.client as w

pythoncom.CoInitialize()
lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
def typed(raw,name):
    ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]==name)
    return w.dynamic.Dispatch(raw,typeinfo=ti)
rot=pythoncom.GetRunningObjectTable()
ctx=pythoncom.CreateBindCtx(0)
en=rot.EnumRunning()
app=None
while True:
    x=en.Next(1)
    if not x:break
    mon=x[0]
    if mon.GetDisplayName(ctx,None)=='36084EFDApiLibROT':
        app=typed(rot.GetObject(mon).QueryInterface(pythoncom.IID_IDispatch),'IApplication')
        break
if not app:raise RuntimeError('Flow API not in ROT')
doc=typed(app.GetActiveDoc(),'IDocument')
print('before',doc.GetProjectsCount(),flush=True)
p=doc.CreateProject(None)
print('created',bool(p),flush=True)
if p:
    p=typed(p,'IProject')
    print('name before',p.GetName(),flush=True)
    p.SetName('PT-SHT-10-demo-Q10')
    print('name after',p.GetName(),flush=True)
    print('config',p.GetConfiguration().GetName(),flush=True)
    print('add',doc.AddProject(p,'По умолчанию'),flush=True)
    print('after',doc.GetProjectsCount(),flush=True)
    cad=typed(app.GetCAD(),'ICADApplication')
    cdoc=typed(cad.GetActiveDoc(),'ICADDocument')
    print('cad save',cdoc.Save(),flush=True)
