import pythoncom
l=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\EFDApi.tlb')
for i in range(l.GetTypeInfoCount()):
 if l.GetDocumentation(i)[0]!='IGeneralSettings':continue
 t=l.GetTypeInfo(i)
 for h in [50334592,50333056]:
  q=t.GetRefTypeInfo(h);print(h,q.GetDocumentation(-1)[0]);a=q.GetTypeAttr()
  if a.typekind==0:
   for j in range(a.cVars):
    v=q.GetVarDesc(j);print(' ',q.GetDocumentation(v.memid)[0],v.value)
