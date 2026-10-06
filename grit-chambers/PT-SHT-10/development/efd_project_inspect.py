import pythoncom
import win32com.client as w
pythoncom.CoInitialize()
sw=w.Dispatch('SldWorks.Application');expected_moniker=str(sw.GetProcessID)+'EFDApiLibROT'
rot=pythoncom.GetRunningObjectTable();ctx=pythoncom.CreateBindCtx(0);en=rot.EnumRunning();mon=None
while True:
    x=en.Next(1)
    if not x:break
    if x[0].GetDisplayName(ctx,None)==expected_moniker:mon=x[0];break
if not mon:raise RuntimeError('Flow process not found')
lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
def typed(obj,name):
    ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]==name)
    return w.dynamic.Dispatch(obj,typeinfo=ti)
app=typed(rot.GetObject(mon).QueryInterface(pythoncom.IID_IDispatch),'IApplication')
doc=typed(app.GetActiveDoc(),'IDocument')
p=typed(doc.GetActiveProject(),'IProject')
print('project',p.GetName())
g=typed(p.GetGeneralSettings(),'IGeneralSettings')
for n in ['GetProblemType','GetTransient','GetGravitation','GetFlowSpaceType','GetFluidFlow','GetFluidType','GetFlowType','GetConduction','GetDefaultMeshSettings']:
    try:
        x=getattr(g,n)
        v=x() if n!='GetDefaultMeshSettings' else None
        print(n,v)
    except Exception as exc:print(n,'ERR',repr(exc))
print('project substances',p.GetProjectSubstances())
print('features',p.GetFeatures())
