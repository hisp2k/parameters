from pathlib import Path
import sys,json,copy,math,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
original=json.loads(bridge.STATE.read_text(encoding='utf-8'))
out=base/'geometry_after_fixes_20261005.json'
rows=json.loads(out.read_text(encoding='utf-8')) if out.exists() else []
def geometry():
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY))
 g=bridge.measured_geometry(top)
 return {'tube_outer_diameter_mm':g['tube_diameter'],
         'tube_full_length_mm':g['working_length']+270,
         'world_axis':g['world_axis'],'inclination_to_horizontal_deg':g['incline']}
try:
 baseline=geometry();print('baseline geometry',baseline,flush=True)
 for key,value in [('tube_diameter',145),('incline',50)]:
  if any(r['parameter']==key and r['applied'] and 'restored_geometry' in r for r in rows):continue
  rows=[r for r in rows if r['parameter']!=key]
  row={'parameter':key,'before':original['values'][key],'tested':value,'baseline_geometry':baseline}
  try:
   v=copy.deepcopy(original['values']);v[key]=value
   r=bridge.apply(v,sw,original['selection'],original['design_mode']);assert r['ok'],r
   row.update(applied=True,verification=r['cad_verification'],geometry=geometry(),snapshot=r['snapshot'])
   if key=='tube_diameter':assert abs(row['geometry']['tube_outer_diameter_mm']-value)<1e-6
   if key=='incline':assert abs(row['geometry']['inclination_to_horizontal_deg']-value)<1e-5,row['geometry']
   print(key,'applied verified',row['geometry'],flush=True)
  except Exception as exc:
   row.update(applied=False,errors=[str(exc)]);print(key,'FAILED',str(exc),flush=True)
  finally:
   current=json.loads(bridge.STATE.read_text(encoding='utf-8'))
   if current['values']!=original['values']:
    r=bridge.apply(original['values'],sw,original['selection'],original['design_mode']);assert r['ok'],r
    row['restored_verification']=r['cad_verification']
   else:
    top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY))
    row['restored_issues']=bridge.model_issues(sw,top)
    row['restored_interferences']=bridge.interference_issues(top)
    assert row['restored_issues']==(0,0,[]) and not row['restored_interferences']
    e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    assert top.Save3(13,e,q) and not e.value
   row['restored_geometry']=geometry();rows.append(row)
   out.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
   print(key,'restored',flush=True)
finally:sw.CommandInProgress=previous
