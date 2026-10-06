import pythoncom
import win32com.client as w
pythoncom.CoInitialize()
rot=pythoncom.GetRunningObjectTable()
ctx=pythoncom.CreateBindCtx(0)
en=rot.EnumRunning()
mon=None
while True:
    x=en.Next(1)
    if not x:break
    if x[0].GetDisplayName(ctx,None)=='36084EFDApiLibROT':
        mon=x[0];break
if not mon:raise RuntimeError('Flow process not found')
lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
def typed(obj,name):
    ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]==name)
    return w.dynamic.Dispatch(obj,typeinfo=ti)
app=typed(rot.GetObject(mon).QueryInterface(pythoncom.IID_IDispatch),'IApplication')
cad=typed(app.GetCAD(),'ICADApplication')
doc=typed(cad.GetActiveDoc(),'ICADDocument')
print('path',doc.GetPathName())
print('save',doc.Save())
