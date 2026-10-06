from pathlib import Path
import sys,json,shutil,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));docs=bridge.open_models(sw);tube=docs['tube']
 backup=base/'snapshots/20261005-before-horizontal-angle';assert not backup.exists()
 for p in {Path(c.GetPathName) for c in top.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}:
  if p.is_file() and p.is_relative_to(base):
   dest=backup/p.relative_to(base);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 before=bridge.measured_geometry(top);mgr,globals_=bridge.globals_in(tube);i,old=globals_['Угол наклона']
 try:
  sw.ActivateDoc3(tube.GetPathName,False,2,e);assert not e.value
  added=mgr.Add2(-1,'"Угол транспортера к горизонтали"= 55градусов',True);assert added>=0
  bridge.set_equation(mgr,i,'"Угол наклона"=90градусов - "Угол транспортера к горизонтали"')
  mgr.EvaluateAll;print('tube rebuild',tube.ForceRebuild3(False),flush=True)
  bridge.refresh_cavities(sw,tube);print('tube after context',tube.ForceRebuild3(False),flush=True)
  sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value;print('top rebuild',top.ForceRebuild3(False),flush=True)
  bridge.refresh_cavities(sw,docs['support'])
  sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value;top.ForceRebuild3(False)
  issues=bridge.model_issues(sw,top);geometry=bridge.measured_geometry(top);intersections=bridge.interference_issues(top)
  print('horizontal linkage',geometry,'issues',issues,'intersections',intersections[:8],flush=True)
  (base/'horizontal_angle_link_20261005.json').write_text(json.dumps({'before':before,'after':geometry,'issues':issues,'interferences':intersections,'backup':str(backup)},ensure_ascii=False,indent=2),encoding='utf-8')
  assert issues==(0,0,[]) and abs(geometry['incline']-55)<1e-4 and not intersections
  assert top.Save3(13,e,q) and not e.value
 except Exception:
  sw.ActivateDoc3(tube.GetPathName,False,2,e);bridge.set_equation(mgr,i,old);mgr.EvaluateAll;tube.ForceRebuild3(False);bridge.refresh_cavities(sw,tube)
  sw.ActivateDoc3(top.GetPathName,False,2,e);top.ForceRebuild3(False);bridge.refresh_cavities(sw,docs['support']);sw.ActivateDoc3(top.GetPathName,False,2,e);top.ForceRebuild3(False)
  assert bridge.model_issues(sw,top)==(0,0,[]) and not bridge.interference_issues(top)
  assert top.Save3(13,e,q) and not e.value
  raise
finally:sw.CommandInProgress=prev
