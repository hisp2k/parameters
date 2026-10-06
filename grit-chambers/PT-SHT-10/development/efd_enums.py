import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 n=l.GetDocumentation(i)[0]
 if 'FeatureType' in n or 'Boundary' in n or 'ParamType' in n or n.startswith('efd') and ('Feature' in n or 'Parameter' in n):
  t=l.GetTypeInfo(i);a=t.GetTypeAttr();print(n,'kind',a.typekind)
  if a.typekind==0:
   for j in range(a.cVars):
    v=t.GetVarDesc(j);print(' ',t.GetDocumentation(v.memid)[0],v.value)
