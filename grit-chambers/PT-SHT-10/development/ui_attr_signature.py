import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]!='IDocumentApi':continue
 t=l.GetTypeInfo(i)
 for j in range(t.GetTypeAttr().cFuncs):
  f=t.GetFuncDesc(j)
  if 'CreateAttributeOnComponentSolidBodyTopology'==t.GetNames(f.memid)[0]:print(f.args,f.rettype)
