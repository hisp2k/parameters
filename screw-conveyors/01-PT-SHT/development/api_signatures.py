import pythoncom,sys
lib=pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
for i in range(lib.GetTypeInfoCount()):
 ti=lib.GetTypeInfo(i);name=ti.GetDocumentation(-1)[0]
 if name not in sys.argv[1:2]:continue
 for j in range(ti.GetTypeAttr().cFuncs):
  desc=ti.GetFuncDesc(j);names=ti.GetNames(desc[0])
  if len(sys.argv)>2 and not any(s.lower() in names[0].lower() for s in sys.argv[2:]):continue
  print(names,desc)
