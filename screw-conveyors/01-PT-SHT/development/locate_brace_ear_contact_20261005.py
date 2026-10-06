from pathlib import Path
import sys,json,pythoncom,traceback
import win32com.client as w
from brace_clearance_20261005 import local_point
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');state=json.loads(bridge.STATE.read_text(encoding='utf-8'));original=bridge.interference_issues

def locate(top):
 rows=original(top)
 if rows:
  print('Contacts found',rows,flush=True)
  mgr=top.InterferenceDetectionManager;mgr.TreatCoincidenceAsInterference=False;mgr.TreatSubAssembliesAsComponents=False;mgr.IncludeMultibodyPartInterferences=True;mgr.IgnoreHiddenBodies=False
  result=[]
  try:
   for item in mgr.GetInterferences or []:
    if item.Volume*1e9<=.001:continue
    components=list(item.Components);brace=next(c for c in components if 'Подкос' in c.Name2)
    print('Read contact body',flush=True)
    dispid=item._oleobj_.GetIDsOfNames('GetInterferenceBody')
    body=w.Dispatch(item._oleobj_.Invoke(dispid,0,pythoncom.DISPATCH_METHOD,True))
    print("Interference body",bool(body),flush=True)
    mass=list(body.GetMassProperties(1));box=body.GetBodyBox;box=list(box() if callable(box) else box)
    t=list(brace.Transform2.ArrayData)
    corners=[local_point([box[3*ix],box[1+3*iy],box[2+3*iz]],t) for ix in (0,1) for iy in (0,1) for iz in (0,1)]
    result.append({'components':[c.Name2 for c in components],'volume_mm3':mass[3]*1e9,'world_center':mass[:3],'local_center':local_point(mass[:3],t),'local_bbox':[min(p[i] for p in corners) for i in range(3)]+[max(p[i] for p in corners) for i in range(3)]})
  except Exception:
   traceback.print_exc();raise
  finally:mgr.Done()
  (base/'brace_ear_interference_location_20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('Located contacts',result,flush=True)
 return rows
try:
 bridge.interference_issues=locate;v=dict(state['values']);v['incline']=35;bridge.apply(v,sw,state['selection'],state['design_mode'])
except bridge.ApplyError as exc:
 print('Expected reject; verified restored',exc.details.get('rollback_verified'),'Error',str(exc),flush=True)
 (base/'brace_ear_location_failure_20261005.json').write_text(json.dumps({'error':str(exc),'details':exc.details},ensure_ascii=False,indent=2),encoding='utf-8')
finally:bridge.interference_issues=original
