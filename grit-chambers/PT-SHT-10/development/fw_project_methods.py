import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]=='IProjectApiHandler':
  t=l.GetTypeInfo(i)
  for j in range(t.GetTypeAttr().cFuncs):
   f=t.GetFuncDesc(j);n=t.GetNames(f.memid)[0]
   if any(x in n.lower() for x in ['rebuild','boundary','fluid','domain','mesh','check','volume','reference']):print(n,f.args,flush=True)
