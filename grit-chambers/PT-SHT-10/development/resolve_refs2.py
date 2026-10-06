import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]!='ICADDocument':continue
 t=l.GetTypeInfo(i)
 for h in [50353792,50354176]:
  try:print(h,t.GetRefTypeInfo(h).GetDocumentation(-1))
  except Exception as e:print(h,e)
