import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 n=l.GetDocumentation(i)[0]
 if 'Fluid' in n and l.GetTypeInfo(i).GetTypeAttr().typekind==0:
  t=l.GetTypeInfo(i);print(n)
  for j in range(t.GetTypeAttr().cVars):
   v=t.GetVarDesc(j);print(' ',t.GetDocumentation(v.memid)[0],v.value)
