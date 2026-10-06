import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 n=l.GetDocumentation(i)[0]
 if any(s in n for s in ['FlowSpace','ProblemType','FlowType']):
  t=l.GetTypeInfo(i);a=t.GetTypeAttr()
  print(n,a.typekind,flush=True)
  if a.typekind==0:
   for j in range(a.cVars):
    v=t.GetVarDesc(j);print(' ',t.GetNames(v.memid),v.value,flush=True)
