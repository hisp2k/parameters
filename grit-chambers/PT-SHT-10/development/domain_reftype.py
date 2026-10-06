import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]=='IGeneralSettings':
  t=l.GetTypeInfo(i)
  r=t.GetRefTypeInfo(50332288)
  print(r.GetDocumentation(-1),r.GetTypeAttr().typekind,flush=True)
  for j in range(r.GetTypeAttr().cVars):
   v=r.GetVarDesc(j);print(r.GetNames(v.memid),v.value,flush=True)
