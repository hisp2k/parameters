from pathlib import Path
import sys,json,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
rows=[]
try:
 for kind,path in {'top':bridge.TOP_ASSEMBLY,**bridge.FILES}.items():
  d=sw.GetOpenDocumentByName(str(path));eq=d.GetEquationMgr
  row={'kind':kind,'equations':[eq.Equation(i) for i in range(eq.GetCount)],'mates':[]}
  f=d.FirstFeature
  while f:
   if f.GetTypeName2=='MateGroup':
    m=f.GetFirstSubFeature
    while m:
     if m.GetTypeName2=='MateAngle' or kind=='top':
      row['mates'].append({'name':m.Name,'type':m.GetTypeName2,'error':m.GetErrorCode,
       'components':[m.GetSpecificFeature2.MateEntity(i).ReferenceComponent.Name2 if m.GetSpecificFeature2.MateEntity(i).ReferenceComponent else 'assembly' for i in range(m.GetSpecificFeature2.GetMateEntityCount)]})
     m=m.GetNextSubFeature
   f=f.GetNextFeature
  rows.append(row)
 out=base/'geometry_dependencies_20261005.json';out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(rows,ensure_ascii=False,indent=2),flush=True)
finally:sw.CommandInProgress=previous
