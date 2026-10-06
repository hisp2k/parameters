import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for n in ['IProjectFeatures','IBoundaryCondition']:
 for i in range(l.GetTypeInfoCount()):
  if l.GetDocumentation(i)[0]!=n:continue
  t=l.GetTypeInfo(i)
  for h in [50354560,50355072,50355200]:
   try:print(n,h,t.GetRefTypeInfo(h).GetDocumentation(-1)[0])
   except Exception as e:print(n,h,e)
