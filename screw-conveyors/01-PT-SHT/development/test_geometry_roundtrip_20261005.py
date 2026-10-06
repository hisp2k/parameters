from pathlib import Path
import copy,json,sys,traceback,pythoncom
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve()
sys.path.insert(0,str(base))
import bridge
from open_assembly import model_issues
sw=w.GetActiveObject('SldWorks.Application')
original=json.loads(bridge.STATE.read_text(encoding='utf-8'))
original['values'].update(working_length=2510,tube_diameter=141,incline=55)
out=base/'geometry_roundtrip_20261005.json'
rows=json.loads(out.read_text(encoding='utf-8')) if out.exists() else []

def audit():
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY))
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 sw.ActivateDoc3(top.GetPathName,False,2,e)
 assert not e.value
 issues=model_issues(sw,top)
 mgr=top.InterferenceDetectionManager
 mgr.TreatCoincidenceAsInterference=False
 mgr.TreatSubAssembliesAsComponents=False
 mgr.IncludeMultibodyPartInterferences=True
 mgr.IgnoreHiddenBodies=False
 mgr.MakeInterferingPartsTransparent=False
 mgr.CreateFastenersFolder=False
 try:
  raw=[{'components':[c.Name2 for c in item.Components or []],
        'volume_mm3':float(item.Volume)*1e9} for item in mgr.GetInterferences or []]
 finally: mgr.Done()
 return {'suppressed':issues[0],'broken_mates':issues[1],'feature_errors':issues[2],
         'contacts':len(raw),'positive_interferences':[r for r in raw if r['volume_mm3']>.001]}

def save_restored():
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY))
 assert model_issues(sw,top)==(0,0,[]),'Rollback model has errors'
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 assert top.Save3(13,e,q) and not e.value,(e.value,q.value)

for key,value in [('working_length',2610),('tube_diameter',145),('incline',50)]:
 if any(r['parameter']==key for r in rows):continue
 row={'parameter':key,'before':original['values'][key],'tested':value}
 try:
  v=copy.deepcopy(original['values']);v[key]=value
  current=json.loads(bridge.STATE.read_text(encoding='utf-8'))
  result=current | {'ok':True} if current['values']==v else bridge.apply(v,sw,original['selection'],original['design_mode'])
  row['applied']=result['ok'];row['snapshot']=result.get('snapshot')
  if result['ok']:
   print('applied',key,flush=True)
   row['audit']=audit()
   print('audited',key,'positive',len(row['audit']['positive_interferences']),flush=True)
   docs=bridge.open_models(sw)
   row['equations']={kind:bridge.globals_in(docs[kind])[1][name][1] for kind,name in bridge.FIELDS[key]}
  else: row['errors']=result['errors']
 except Exception as exc:
  row['applied']=False;row['errors']=[str(exc)]
  print('FAILED',key,str(exc),flush=True)
  save_restored()
 finally:
  rows.append(row);out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
  save_restored() # Native interference detection can dirty the assembly without changing geometry.
  current=json.loads(bridge.STATE.read_text(encoding='utf-8'))
  if current['values']!=original['values']:
   r=bridge.apply(original['values'],sw,original['selection'],original['design_mode'])
   assert r['ok'],r
  row['restored_audit']=audit()
  assert not row['restored_audit']['positive_interferences'],row['restored_audit']
  save_restored()
  out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
  print(key,'applied',row['applied'],'positive',len(row.get('audit',{}).get('positive_interferences',[])),'restored OK',flush=True)
