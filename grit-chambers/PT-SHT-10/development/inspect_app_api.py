import win32com.client as w
s=w.Dispatch('SldWorks.Application');o=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI()
ti=o._oleobj_.GetTypeInfo();a=ti.GetTypeAttr()
for j in range(a.cFuncs):
 f=ti.GetFuncDesc(j);print(ti.GetNames(f.memid))
