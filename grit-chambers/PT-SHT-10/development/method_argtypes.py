import pythoncom
for path,target,methods in [(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb','IProject',['CreateAttribute','GetEntity']),(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll','IProjectApiHandler',['UpdateFeatureTopolReferenciesFromSelection','FeatureAddFaces','CreateTemplateBoundaryCondition']),(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll','IBoundaryConditionAPI',['ApplyUIChanges','GetParameter'])]:
 l=pythoncom.LoadTypeLib(path)
 for i in range(l.GetTypeInfoCount()):
  if l.GetDocumentation(i)[0]!=target:continue
  t=l.GetTypeInfo(i);a=t.GetTypeAttr()
  print('\n',target)
  for j in range(a.cFuncs):
   f=t.GetFuncDesc(j);name=t.GetNames(f.memid)[0]
   if name in methods:
    print(name,'args',f.args,'return',f.rettype)
