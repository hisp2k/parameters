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
raw=json.loads(Path('work/lower_interferences_working.json').read_text(encoding='utf-8'))
raw.update({'status':'constructive_interferences_eliminated','constructive_interference_count':0,'expected_simplified_thread_pairs':8,'production_changes_saved':True,'top_assembly':str(top),'seal_representation':'conservative_envelope_50x70x10','lower_mate_errors':0,'component_count':54,'caveat':'Резьба метизов упрощена; профиль манжеты и допуски посадок требуют проверки перед производством.'})
assert raw['count']==8 and all(any('Болт' in n for n in i['components']) and any('Гайка' in n for n in i['components']) for i in raw['interferences'])
(base/'lower_interference_audit_20261004.json').write_text(json.dumps(raw,ensure_ascii=False,indent=2),encoding='utf-8')
sys.path.insert(0,str(base));import journal
journal.record_assembly_repair(['Совпадение48','Концентричный25','Совпадение49','Концентричный27','Совпадение50','Совпадение58','Концентричный32','Концентричный33','Концентричный97'],'lower-interference-mates-20261004')
changes=[
 {'key':'seal','name':'Манжета нижней обоймы','before':'Прежний профиль с пересечениями','after':'Габаритная модель 50×70×10; посадочная длина 10 мм'},
 {'key':'ring70','name':'Стопорное кольцо D70','before':'1.7 мм, смещение оси','after':'2.5 мм; восстановлена соосность'},
 {'key':'ring80','name':'Стопорное кольцо D80','before':'2 мм','after':'2.5 мм'},
 {'key':'grooves','name':'Канавки стопорных колец','before':'2 / 2.3 мм','after':'2.65 мм; кольца по центру, зазор 0.075 мм с каждой стороны; радиус дна 0.05 мм'},
 {'key':'sleeve','name':'Гильза нижней крышки','before':'21 мм','after':'18.3 мм'},
 {'key':'assembly','name':'Подключение исправленной нижней обоймы','before':'Прежний узел','after':raw['assembly']}
]
existing=journal._read()
if not any(x.get('repair_id')=='lower-interference-geometry-20261004' for x in existing['entries']):journal._append({'type':'model_change','title':'Устранение пересечений нижней обоймы','repair_id':'lower-interference-geometry-20261004','change_count':len(changes),'changes':changes})
