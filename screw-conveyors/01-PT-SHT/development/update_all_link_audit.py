from pathlib import Path
import json,sys
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sw=w.GetActiveObject('SldWorks.Application')
top=base/'CAD_восстановленный'/"PT.SHT.01.20.00.00 СБ 'Шнек 1' — восстановлено.SLDASM"
doc=sw.GetOpenDocumentByName(str(top))
docs={str(top):doc}
components=doc.GetComponents(False)
for c in components:
 d=c.GetModelDoc2
 if d and d.GetType==2:docs[d.GetPathName]=d
report=[]
for path,d in docs.items():
 errors=[];f=d.FirstFeature
 while f:
  if f.GetErrorCode and f.GetTypeName2!='MateGroup':errors.append({'name':f.Name,'type':f.GetTypeName2,'code':int(f.GetErrorCode)})
  if f.GetTypeName2=='MateGroup':
   m=f.GetFirstSubFeature
   while m:
    if m.GetErrorCode:
     entry={'name':m.Name,'type':m.GetTypeName2,'code':int(m.GetErrorCode),'entities':[]}
     for i in range(2):
      try:
       e=m.GetSpecificFeature2.MateEntity(i);c=e.ReferenceComponent
       entry['entities'].append({'component':c.Name2,'path':c.GetPathName,'reference_present':e.Reference is not None,'params':list(e.EntityParams or [])})
      except Exception:pass
     errors.append(entry)
    m=m.GetNextSubFeature
  f=f.GetNextFeature
 report.append({'assembly':path,'errors':errors})
 print(Path(path).name,'errors',len(errors),flush=True)
(base/'mate_diagnostics_20261004.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
paths=list(sw.GetDocumentDependencies2(str(top),True,False,False)[1::2]);missing=[p for p in paths if not Path(p).is_file()]
(base/'recovered_assembly_check.json').write_text(json.dumps({'assembly':str(top),'dependency_count':len(paths),'missing':missing,'paths':paths},ensure_ascii=False,indent=2),encoding='utf-8')
print('saved top dirty',doc.GetSaveFlag,'components',len(components),'missing',missing,flush=True)

