from pathlib import Path
import sys,json,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']));rows=[]
 for c in tube.GetComponents(True):
  if 'Ухо' not in c.Name2 and 'Подкос' not in c.Name2:continue
  d=c.GetModelDoc2;f=d.FirstFeature
  while f:
   if f.GetTypeName2=='Cavity':
    data=f.GetDefinition
    access=data.AccessSelections(tube,c)
    rows.append({'part':c.Name2,'feature':f.Name,'components':[(x.Name2,x.GetPathName) for x in data.Components or []],
      'part_path':d.GetPathName,'part_config':d.ConfigurationManager.ActiveConfiguration.Name})
    print('access',access,'count',data.GetComponentsCount,flush=True)
    if access:data.ReleaseSelectionAccess
   f=f.GetNextFeature
 print(json.dumps(rows,ensure_ascii=False,indent=2),flush=True)
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 assert top.Save3(13,e,q) and not e.value
finally:sw.CommandInProgress=prev
