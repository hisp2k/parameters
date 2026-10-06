from pathlib import Path
import sys,json,shutil,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));tube=sw.GetOpenDocumentByName(str(bridge.FILES['tube']))
 paths={Path(c.GetPathName) for c in top.GetComponents(False) or [] if c.GetPathName}|{bridge.TOP_ASSEMBLY}
 backup=base/'snapshots/20261005-before-parametric-interface'
 assert not backup.exists()
 for p in paths:
  if p.is_file() and p.is_relative_to(base):
   dest=backup/p.relative_to(base);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 sw.ActivateDoc3(tube.GetPathName,False,2,e);assert not e.value
 mgr=tube.GetEquationMgr
 found=[(i,mgr.Equation(i)) for i in range(mgr.GetCount) if '"D2@Эскиз1@' in mgr.Equation(i) and 'Фланец трубы шнека' in mgr.Equation(i)]
 assert len(found)==1,found
 i,old=found[0];new=old.split('=')[0]+'= 170мм'
 bridge.set_equation(mgr,i,new);mgr.EvaluateAll;assert tube.ForceRebuild3(False)
 sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value;assert top.ForceRebuild3(False)
 assert bridge.model_issues(sw,top)==(0,0,[])
 assert not bridge.interference_issues(top)
 assert top.Save3(13,e,q) and not e.value
 (base/'flange_interface_fix_20261005.json').write_text(json.dumps({'before':old,'after':new,'backup':str(backup),'issues':0,'interferences':0},ensure_ascii=False,indent=2),encoding='utf-8')
 print('flange PCD fixed at 170mm, errors/interferences 0',flush=True)
finally:sw.CommandInProgress=previous
