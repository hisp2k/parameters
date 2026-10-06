import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 n=l.GetDocumentation(i)[0]
 if any(k.lower() in n.lower() for k in ['BoundaryConditionType','BCType','ParamState','Topol','EntityType']):
  t=l.GetTypeInfo(i);a=t.GetTypeAttr()
  if a.typekind==0:
   print(n)
   for j in range(a.cVars):
    v=t.GetVarDesc(j);print(' ',t.GetDocumentation(v.memid)[0],v.value)
