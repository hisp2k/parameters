import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 t=l.GetTypeInfo(i);a=t.GetTypeAttr()
 if a.typekind!=4:continue
 nm=l.GetDocumentation(i)[0]
 vals=[]
 for j in range(a.cFuncs):
  f=t.GetFuncDesc(j);n=t.GetNames(f.memid)[0]
  if any(x in n.lower() for x in ['geometry','leak','volume','fluidregion','fluidvolume','check']):vals.append(n)
 if vals:print(nm,vals)
