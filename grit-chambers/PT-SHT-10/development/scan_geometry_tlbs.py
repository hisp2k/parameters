import pythoncom
from pathlib import Path
root=Path(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW')
for filename in ['floworks.tlb','NIKAPI.tlb','EFDApiSrv.tlb']:
 try:l=pythoncom.LoadTypeLib(str(root/filename))
 except Exception as e:print(filename,repr(e));continue
 print('\nLIB',filename,'types',l.GetTypeInfoCount())
 for i in range(l.GetTypeInfoCount()):
  t=l.GetTypeInfo(i);a=t.GetTypeAttr();nm=l.GetDocumentation(i)[0]
  if a.typekind not in (3,4):continue
  hits=[]
  for j in range(a.cFuncs):
   f=t.GetFuncDesc(j);n=t.GetNames(f.memid)[0]
   if any(s in n.lower() for s in ['checkgeom','fluidvolume','invalidcontact','leak','fluidregion']):hits.append((t.GetNames(f.memid),f.args,f.rettype))
  if hits:print(nm,hits)
