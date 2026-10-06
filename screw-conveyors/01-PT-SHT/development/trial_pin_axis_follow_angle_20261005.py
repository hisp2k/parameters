from pathlib import Path
from datetime import datetime
import sys,json,math,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
try:
 root=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));sw.ActivateDoc3(root.GetPathName,False,2,e);assert not e.value
 stamp=datetime.now().strftime('%Y%m%d_%H%M%S');folder=(Path('work')/('pin-joint-trial-'+stamp)).resolve();folder.mkdir();target=folder/'Сборка — цепочка ухо-втулка-подкос.SLDASM'
 assert root.Extension.SaveAs2(str(target),0,7,w.VARIANT(pythoncom.VT_DISPATCH,None),'_PIN_'+stamp,False,e,q) and not e.value,(e.value,q.value)
 spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True;trial=sw.OpenDoc7(spec);assert trial
 sw.ActivateDoc3(str(target),False,2,e);assert not e.value
 print('Copied independent root',str(target),flush=True)
 outside=[c.GetPathName for c in trial.GetComponents(False) if c.GetPathName and not Path(c.GetPathName).resolve().is_relative_to(folder)]
 assert not outside,outside
 support=next(c.GetModelDoc2 for c in trial.GetComponents(True) if 'Опора шнековая' in c.Name2)
 sw.ActivateDoc3(support.GetPathName,False,2,e);assert not e.value
 support.Parameter('D1@ПЛОСКОСТЬ3').SystemValue=math.radians(40)
 rebuilt=support.ForceRebuild3(False);print('Support skeleton angle 20 to 40',rebuilt,flush=True)
 sw.ActivateDoc3(trial.GetPathName,False,2,e);rebuilt=trial.ForceRebuild3(False);print('Root rebuilt',rebuilt,flush=True)
 issues=bridge.model_issues(sw,trial);print('Issues',issues,flush=True)
 joints=[]
 for c in trial.GetComponents(False):
  if not any(s in c.Name2 for s in ("'Втулка'","'Ухо'")):continue
  t=list(c.Transform2.ArrayData)
  for b in c.GetModelDoc2.GetBodies2(0,True):
   for f in b.GetFaces():
    surface=f.GetSurface
    if not surface.IsCylinder:continue
    params=list(surface.CylinderParams)
    if abs(params[6]*2000-(18 if "'Втулка'" in c.Name2 else 10.8))>1e-6:continue
    point=[sum(params[j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]
    joints.append({'component':c.Name2,'point':point})
 print('Axes',joints,flush=True)
 intersections=bridge.interference_issues(trial);print('Intersections',intersections[:15],'count',len(intersections),flush=True)
 (base/'pin_joint_trial_20261005.json').write_text(json.dumps({'root':str(target),'issues':issues,'joints':joints,'interferences':intersections},ensure_ascii=False,indent=2),encoding='utf-8')
finally:
 sw.ActivateDoc3(str(bridge.TOP_ASSEMBLY),False,2,e);sw.CommandInProgress=prev
