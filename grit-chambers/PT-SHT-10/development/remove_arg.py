import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]!='IProjectFeatures':continue
 t=l.GetTypeInfo(i)
 for j in range(t.GetTypeAttr().cFuncs):
  f=t.GetFuncDesc(j)
  if t.GetNames(f.memid)[0]=='RemoveFeature':print(f.args,f.rettype)
