import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 n=l.GetDocumentation(i)[0]
 if 'Solver' in n or n in ('ICalculationControlOptions','IProjectFeatures'):
  t=l.GetTypeInfo(i);a=t.GetTypeAttr()
  if a.typekind!=4:continue
  print('\n',n)
  for j in range(a.cFuncs):
   f=t.GetFuncDesc(j); print(' ',t.GetNames(f.memid)[0],t.GetNames(f.memid)[1:])
