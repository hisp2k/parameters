import win32com.client as w
s=w.Dispatch('SldWorks.Application')
o=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')
print('obj',o)
if o:
 ti=o._oleobj_.GetTypeInfo();print('type',ti.GetDocumentation(-1))
 a=ti.GetTypeAttr();print('count',a.cFuncs)
 for j in range(a.cFuncs):
  f=ti.GetFuncDesc(j);print(ti.GetNames(f.memid))
