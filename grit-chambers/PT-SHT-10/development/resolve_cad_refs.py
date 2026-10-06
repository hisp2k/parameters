import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]=='ICADDocument':
  t=l.GetTypeInfo(i)
  for j in range(t.GetTypeAttr().cFuncs):
   f=t.GetFuncDesc(j)
   if t.GetNames(f.memid)[0] in ['GetEntity2','GetEntities']:
    print(t.GetNames(f.memid)[0],f.args,f.rettype)
