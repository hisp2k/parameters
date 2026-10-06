import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
for i in range(l.GetTypeInfoCount()):
 n=l.GetDocumentation(i)[0]; t=l.GetTypeInfo(i);a=t.GetTypeAttr()
 if a.typekind!=0:continue
 if any(k.lower() in n.lower() for k in ['referenc','topol','entity']):
  print(n)
  for j in range(a.cVars):
   v=t.GetVarDesc(j);print(' ',t.GetDocumentation(v.memid)[0],v.value)
