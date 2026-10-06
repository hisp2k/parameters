from pathlib import Path
import sys,json,shutil,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 ear=next(c for c in tube.GetComponents(True) if 'Ухо' in c.Name2 and c.Name2.endswith('-1'))
 pipe=next(c for c in tube.GetComponents(True) if 'Труба шнека' in c.Name2)
 part=ear.GetModelDoc2
 part.FeatureManager.EditRollback(1,'')
 backup=base/'snapshots/20261005-before-ear-context';assert not backup.exists()
 paths={Path(c.GetPathName) for c in top.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}
 for p in paths:
  if p.is_file() and p.is_relative_to(base):
   dest=backup/p.relative_to(base);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value
 mgr=top.GetEquationMgr;assert mgr.GetCount==1
 old=mgr.Equation(0);bridge.set_equation(mgr,0,old.split('=')[0]+'= 141мм');mgr.EvaluateAll
 sw.ActivateDoc3(part.GetPathName,False,2,e);assert not e.value
 f=part.FeatureByName('Подрезка уха по корпусу');assert f
 part.ClearSelection2(True);assert f.Select2(False,0);assert part.Extension.DeleteSelection2(0)
 sw.ActivateDoc3(tube.GetPathName,False,2,e);assert not e.value
 tube.ClearSelection2(True);assert ear.Select4(False,tube.SelectionManager.CreateSelectData,False)
 info=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 print('edit part',tube.EditPart2(True,False,info),info.value,flush=True)
 try:
  tube.ClearSelection2(True);assert pipe.Select4(False,tube.SelectionManager.CreateSelectData,False)
  tube.InsertCavity4(0.,0.,0.,True,0,-1)
  f=part.FeatureByName('Полость1');assert f and not f.GetErrorCode
  f.Name='Подрезка уха — рабочий корпус'
 finally:tube.EditAssembly()
 print('new cavity created',flush=True)
 assert tube.ForceRebuild3(False)
 sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value;assert top.ForceRebuild3(False)
 assert bridge.model_issues(sw,top)==(0,0,[])
 assert not bridge.interference_issues(top)
 assert top.Save3(13,e,q) and not e.value
 (base/'ear_context_and_gasket_fix_20261005.json').write_text(json.dumps({'gasket_before':old,'gasket_after':mgr.Equation(0),'backup':str(backup),'issues':0,'interferences':0},ensure_ascii=False,indent=2),encoding='utf-8')
 print('ear context + gasket restored, errors/interferences 0',flush=True)
finally:sw.CommandInProgress=prev
