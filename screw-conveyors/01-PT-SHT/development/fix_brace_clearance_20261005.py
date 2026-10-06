"""Verify cuts in separate parts, then repair under the normal CAD transaction guards."""
from pathlib import Path
from datetime import datetime
import sys,json,shutil
import pythoncom,win32com.client as w
from brace_bypass_20261005 import create_bypass
from brace_clearance_20261005 import create_clearance,world_point,local_point,local_vector,dot,unit
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge,journal,server
sw=w.GetActiveObject('SldWorks.Application')
request=json.loads(Path('work/requested_cad_parameters_20261005.json').read_text(encoding='utf-8'))
before=json.loads(bridge.STATE.read_text(encoding='utf-8'))
assert before['values']['incline']==35 and request['values']['incline']==55
original_interference=bridge.interference_issues
repairs=[];live_parts=[];done=False
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
trial_dir=Path('work')/datetime.now().strftime('brace-clearance-trial-%Y%m%d-%H%M%S');trial_dir.mkdir()

def volume(part):return sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True))*1e9
def activate(part):
 sw.ActivateDoc3(part.GetPathName,False,2,e);assert not e.value and sw.ActiveDoc.GetPathName==part.GetPathName

def repair_if_needed(top):
 global done
 intersections=original_interference(top)
 if done or not intersections:return intersections
 assert abs(bridge.measured_geometry(top)['incline']-55)<1e-6
 assert all(any('Подкос' in name for name in row['components']) and any(any(k in name for k in ('Труба шнека','Винт шнека')) for name in row['components']) for row in intersections),intersections
 components=list(top.GetComponents(False));pipe=next(c for c in components if 'Труба шнека' in c.Name2)
 transform=list(pipe.Transform2.ArrayData);part=pipe.GetModelDoc2
 surface=max([f for b in part.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder and abs(f.GetSurface.CylinderParams[6]*2000-133)<1e-6],key=lambda f:f.GetArea).GetSurface
 cylinder=list(surface.CylinderParams)
 axis_point=world_point(cylinder[:3],transform)
 axis=unit([sum(cylinder[3+j]*transform[j*3+i] for j in range(3)) for i in range(3)])
 braces=[c for c in components if 'Подкос' in c.Name2]
 assert len(braces)==2 and len({c.GetPathName for c in braces})==2
 planned=[]
 for index,component in enumerate(braces):
  native=component.GetModelDoc2;t=list(component.Transform2.ArrayData)
  box=list(native.GetPartBox(True));body_center=world_point([(box[i]+box[i+3])/2 for i in range(3)],t)
  projected=[axis_point[i]+axis[i]*dot([body_center[j]-axis_point[j] for j in range(3)],axis) for i in range(3)]
  center=local_point(projected,t);direction=local_vector(axis,t)
  trial_path=(trial_dir/f'Подкос {index+1} — {trial_dir.name}.SLDPRT').resolve();shutil.copy2(native.GetPathName,trial_path)
  spec=sw.GetOpenDocSpec(str(trial_path));spec.DocumentType=1;spec.Silent=True;trial=sw.OpenDoc7(spec);assert trial
  activate(trial);old_volume=volume(trial);body_count=len(trial.GetBodies2(0,True))
  bypass=create_bypass(sw,trial,center,direction)
  cut=create_clearance(sw,trial,center,direction)
  new_volume=volume(trial);new_body_count=len(trial.GetBodies2(0,True))
  print('Trial',index+1,'volume before/after mm3',old_volume,new_volume,'bodies',body_count,new_body_count,flush=True)
  assert new_body_count==body_count==1,'Clearance must not disconnect the brace'
  assert old_volume<new_volume<2*old_volume,'Unexpected bypass volume'
  assert trial.Save3(9,e,q) and not e.value
  planned.append((component,native,center,direction,cut,bypass,old_volume,new_volume,list(t)))
  sw.CloseDoc(trial.GetTitle)
 for component,native,center,direction,cut,bypass,old_volume,new_volume,t in planned:
  activate(native);native.ForceRebuild3(False)
  f=native.FirstFeature;mirrored=False
  while f:
   mirrored=mirrored or f.GetTypeName2=='MirrorStock';f=f.GetNextFeature
  actual_volume=volume(native)
  print('Live part',component.Name2,'volume',actual_volume,'original/trial',old_volume,new_volume,'mirror',mirrored,flush=True)
  inherited=mirrored and abs(actual_volume-new_volume)<new_volume*.001
  if inherited:
   live_cut={'inherited_from_mirrored_source':True};live_bypass={'inherited_from_mirrored_source':True,'strength_verified':False}
  else:
   assert abs(volume(native)-old_volume)<.001
   live_parts.append(native)
   live_bypass=create_bypass(sw,native,center,direction)
   live_cut=create_clearance(sw,native,center,direction)
  assert len(native.GetBodies2(0,True))==1 and abs(volume(native)-new_volume)<(new_volume*.001 if inherited else .001)
  repairs.append({'component':component.Name2,'file':native.GetPathName,'cut':live_cut,'bypass':live_bypass,'inherited':inherited,'volume_change_mm3':new_volume-old_volume,'before_volume_mm3':old_volume,'trial_volume_mm3':new_volume,'after_volume_mm3':volume(native),'before_transform':t})
 activate(top);assert top.ForceRebuild3(False)
 assert bridge.model_issues(sw,top)==(0,0,[])
 for row,component in zip(repairs,braces):assert max(abs(x-y) for x,y in zip(row['before_transform'],component.Transform2.ArrayData))<1e-7
 done=True
 remaining=original_interference(top)
 print('After repair: remaining intersections',remaining,flush=True)
 return remaining

try:
 bridge.interference_issues=repair_if_needed
 result=bridge.apply(request['values'],sw,request['selection'],request['design_mode'])
 assert result['ok'] and done,result
 bridge.interference_issues=original_interference
 entry=journal.record_apply(before,result)
 outcome=server.save_apply_outcome(request,result)
 proof={'timestamp':datetime.now().astimezone().isoformat(timespec='seconds'),'request':request,'repairs':repairs,'trial_directory':str(trial_dir.resolve()),'result':result,'journal_entry':entry,'outcome':outcome,'strength_verified':False,'fixed_envelope':{'angle_deg':55,'max_tube_diameter_mm':145,'radial_clearance_mm':1}}
 (base/'brace_clearance_fix_20261005.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Requested parameters saved, native checks passed:',result['cad_verification'],flush=True)
except Exception:
 bridge.interference_issues=original_interference
 for part in live_parts:
  activate(part)
  active=part.SketchManager.ActiveSketch
  if active:
   if active.Is3D:part.SketchManager.Insert3DSketch(True)
   else:part.SketchManager.InsertSketch(True)
  for name in ['Проход корпуса — выборка для 55 градусов','Проход корпуса — профиль','Проход корпуса — поперечная плоскость','Ось корпуса 55 градусов — базовые точки']+[n+s for n in ['Полость обхода — нижний переход','Полость обхода — наружная ветвь','Полость обхода — верхний переход','Обход корпуса — нижний переход','Обход корпуса — наружная ветвь','Обход корпуса — верхний переход'] for s in ['', ' — профиль']]:
   feature=part.FeatureByName(name)
   if feature:
    part.ClearSelection2(True);assert feature.Select2(False,0);assert part.Extension.DeleteSelection2(0)
  assert part.ForceRebuild3(False)
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));activate(top);top.ForceRebuild3(False)
 assert bridge.model_issues(sw,top)==(0,0,[]) and not original_interference(top)
 assert top.Save3(13,e,q) and not e.value
 raise
finally:bridge.interference_issues=original_interference
