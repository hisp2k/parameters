import win32com.client as w
s=w.Dispatch('SldWorks.Application');p=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}').GetAPI().IActiveDoc.IActiveProject
b=p.CreateTemplateBoundaryCondition();b.FCType=1;b.Name_='CFD inlet 10 m3h'
print('bc',b.Name_,b.FCType)
for k in [3,18]:
 try:
  x=b.GetParameter(k,'')
  print('param',k,x, x._oleobj_.GetTypeInfo().GetDocumentation(-1) if x else None)
  if x:
   ti=x._oleobj_.GetTypeInfo();a=ti.GetTypeAttr()
   for j in range(a.cFuncs):
    f=ti.GetFuncDesc(j);print(' ',ti.GetNames(f.memid))
 except Exception as e:print('ERR',k,repr(e))
