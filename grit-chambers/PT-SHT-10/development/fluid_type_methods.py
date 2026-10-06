import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]!='IGeneralSettings':continue
 t=l.GetTypeInfo(i)
 for j in range(t.GetTypeAttr().cFuncs):
  f=t.GetFuncDesc(j);n=t.GetNames(f.memid)[0]
  if any(x in n for x in ['FluidType','ProblemType','FluidFlow']):print(n,t.GetNames(f.memid)[1:],f.args)
