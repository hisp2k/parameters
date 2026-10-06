import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for n,ms in [('IProjectFeatures',['AddUpdateFeature','CreateFeature']),('IBoundaryCondition',['Build','AddTopologicalReferenceUUIDAndName','SetTopologicalReferencesUUIDsAndNames','GetParameter'])]:
 for i in range(l.GetTypeInfoCount()):
  if l.GetDocumentation(i)[0]!=n:continue
  t=l.GetTypeInfo(i)
  for j in range(t.GetTypeAttr().cFuncs):
   f=t.GetFuncDesc(j);x=t.GetNames(f.memid)[0]
   if x in ms:print(n,x,f.args,f.rettype)
