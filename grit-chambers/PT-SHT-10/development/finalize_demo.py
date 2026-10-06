import pythoncom,win32com.client as w
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures')
for b in f.GetFeatures2(True,0) or []:
 print('remove invalid BC',b.GetName(),f.RemoveFeature(b.GetUUID()),flush=True)
g=typed(p.GetGeneralSettings(),'IGeneralSettings')
bounds=(-.38,-.02,-.38,.38,.90,.40)
a=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_R8,bounds)
g.SetComputationalDomain(0,a,a)
print('domain',g.GetComputationalDomain(0),flush=True)
print('rebuild',p.Rebuild(True,True,True,False,False,False),'error',p.GetLastRebuildError(),flush=True)
sw=w.Dispatch('SldWorks.Application');assm=sw.ActiveDoc
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',assm.Save3(1,e,v),e.value,v.value,flush=True)
print('reset silent',app.ResetSilent(),flush=True)
lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
attr=lib.GetLibAttr()
try:pythoncom.UnRegisterTypeLib(attr[0],attr[3],attr[4],attr[1],attr[2]);print('unregistered typelib',flush=True)
except Exception as exc:print('unregister error',repr(exc),flush=True)
