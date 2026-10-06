import pythoncom,win32com.client as w
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
t=next(l.GetTypeInfo(i) for i in range(l.GetTypeInfoCount()) if l.GetDocumentation(i)[0]=='ISldWorks')
s=w.dynamic.Dispatch(w.Dispatch('SldWorks.Application')._oleobj_,typeinfo=t)
print('command',s.GetRunningCommandInfo(None,None,None),flush=True)
