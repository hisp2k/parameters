import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]!='IProjectSubstances':continue
 t=l.GetTypeInfo(i)
 for j in range(t.GetTypeAttr().cFuncs):
  f=t.GetFuncDesc(j);print(t.GetNames(f.memid))
