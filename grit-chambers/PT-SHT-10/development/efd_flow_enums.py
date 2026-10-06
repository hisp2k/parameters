import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 n=l.GetDocumentation(i)[0]; t=l.GetTypeInfo(i);a=t.GetTypeAttr()
 if a.typekind!=0:continue
 vals=[]
 for j in range(a.cVars):
  v=t.GetVarDesc(j);nam=t.GetDocumentation(v.memid)[0]
  if any(k.lower() in nam.lower() for k in ['inlet','outlet','volume_flow','volumeflow','normalvolumeflow','pressureopening']):vals.append((nam,v.value))
 if vals:
  print(n)
  for v in vals[:80]:print(' ',v)
