import pythoncom
p=r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb'
l=pythoncom.LoadTypeLib(p)
for target in ['IProjectFeatures','IBoundaryCondition','IParamCollFeature','IProject','IDocument','ICADDocument','IApplication']:
 for i in range(l.GetTypeInfoCount()):
  if l.GetDocumentation(i)[0]!=target: continue
  t=l.GetTypeInfo(i);a=t.GetTypeAttr();print('\n###',target,'functions',a.cFuncs)
  for j in range(a.cFuncs):
   f=t.GetFuncDesc(j); names=t.GetNames(f.memid)
   print(names[0],names[1:], 'inv',f.invkind,'args',len(f.args))
