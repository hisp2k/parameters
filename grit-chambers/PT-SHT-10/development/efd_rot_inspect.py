import pythoncom
import win32com.client as w

pythoncom.CoInitialize()
rot=pythoncom.GetRunningObjectTable()
ctx=pythoncom.CreateBindCtx(0)
en=rot.EnumRunning()
efd=None
while True:
    items=en.Next(1)
    if not items:break
    mon=items[0]
    name=mon.GetDisplayName(ctx,None)
    if name.endswith('EFDApiLibROT'):
        raw=rot.GetObject(mon).QueryInterface(pythoncom.IID_IDispatch)
        lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
        ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]=='IApplication')
        efd=w.dynamic.Dispatch(raw,typeinfo=ti)
        print('moniker',name)
        break
print('object',bool(efd))
if efd:
    print('version',efd.GetVersion())
    d_raw=efd.GetActiveDoc()
    d_ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]=='IDocument')
    doc=w.dynamic.Dispatch(d_raw,typeinfo=d_ti) if d_raw else None
    print('doc',bool(doc),doc.GetTitle() if doc else None)
    if doc:
        try:print('projects',doc.GetProjectsCount())
        except Exception as exc:print('projects error',repr(exc))
        try:
            p=doc.GetActiveProject()
            print('active project',bool(p))
            if p:
                p_ti=next(lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount()) if lib.GetDocumentation(i)[0]=='IProject')
                p=w.dynamic.Dispatch(p,typeinfo=p_ti)
                print('active name',p.GetName())
        except Exception as exc:print('active project error',repr(exc))
