import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 t=l.GetTypeInfo(i);a=t.GetTypeAttr()
 try:n=l.GetDocumentation(i)[0]
 except:n=''
 if 'ComputationalDomain' in n or 'Domain' in n:
  print(n,'kind',a.typekind,flush=True)
  if a.typekind==0:
   for j in range(a.cVars):
    v=t.GetVarDesc(j);print(' ',t.GetNames(v.memid),v.value,flush=True)
