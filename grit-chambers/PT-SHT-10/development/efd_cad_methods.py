import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for target in ['ICADBody','ICADFace','ICADSurface','ICADModelDoc','ICADComponent','IParameter','IFlowBoundaryCondition']:
 for i in range(l.GetTypeInfoCount()):
  if l.GetDocumentation(i)[0]!=target:continue
  t=l.GetTypeInfo(i);a=t.GetTypeAttr();print('\n',target)
  for j in range(a.cFuncs):
   f=t.GetFuncDesc(j);print(t.GetNames(f.memid)[0],t.GetNames(f.memid)[1:])
