import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
for target in ['IBoundaryConditionAPI','IFlowFeatureAPI','IProjectApiHandler']:
 for i in range(l.GetTypeInfoCount()):
  if l.GetDocumentation(i)[0]!=target:continue
  t=l.GetTypeInfo(i);a=t.GetTypeAttr();print('\n',target)
  for j in range(a.cFuncs):
   f=t.GetFuncDesc(j);names=t.GetNames(f.memid)
   if target=='IProjectApiHandler' and not any(x in names[0] for x in ['Feature','CreateTemplate']):continue
   print(names[0],names[1:])
