"""Repair native dependencies, preserving the saved baseline and original files."""
from pathlib import Path
from datetime import datetime
import sys,json,math,shutil
import pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge
sw=w.GetActiveObject('SldWorks.Application');previous=sw.CommandInProgress;sw.CommandInProgress=True
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
added=[];dimension_originals=[];backup=None;cut_original=None
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));docs=bridge.open_models(sw);tube=docs['tube']
 pipe=next(c for c in tube.GetComponents(True) if 'Труба шнека' in c.Name2);pipe_part=pipe.GetModelDoc2
 ear=next(c for c in tube.GetComponents(True) if 'Ухо' in c.Name2);ear_part=ear.GetModelDoc2
 paths={Path(c.GetPathName) for c in top.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}
 opened={Path(d.GetPathName):d for d in sw.GetDocuments if d.GetPathName}
 assert not [p for p in paths if p in opened and opened[p].GetSaveFlag], 'Unsaved CAD must be reviewed first'
 backup=base/'snapshots'/datetime.now().strftime('%Y%m%d-%H%M%S-before-rebuild-dependencies')
 for p in paths:
  if p.is_file() and p.is_relative_to(base):
   dest=backup/p.relative_to(base);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 transform=list(pipe.Transform2.ArrayData);alpha=math.asin(abs(transform[4]));distance=tube.Parameter('D1@Расстояние30').SystemValue
 station=(distance+transform[11])/math.cos(alpha)
 length=pipe_part.Parameter('D1@Вытянуть-Тонкостенный1').SystemValue
 offset=(length-station)*1000
 assert abs(length-2.78)<1e-8 and abs(alpha-math.radians(35))<1e-8
 targets=[(ear_part,'D7@Эскиз1'),(pipe_part,'D1@Плоскость6'),(pipe_part,'D2@Эскиз13'),(tube,'D1@Расстояние30'),(tube,'D1@Расстояние31')]
 dimension_originals=[(doc.Parameter(name),doc.Parameter(name).SystemValue) for doc,name in targets]
 ear_dim=f'D7@Эскиз1@{Path(ear_part.GetPathName).stem}<1>.Part'
 plane=f'D1@Плоскость6@{Path(pipe_part.GetPathName).stem}<1>.Part'
 sketch=f'D2@Эскиз13@{Path(pipe_part.GetPathName).stem}<1>.Part'
 expressions=[
  f'"{ear_dim}" = 24мм + (141мм - "Диаметр трубы") / 2',
  f'"Отступ оси выхода от торца" = {offset:.12f}мм',
  '"Проекция оси выхода" = ("Длина трубы" - 280мм - "Отступ оси выхода от торца") * sin("Угол наклона") + 180мм * cos("Угол наклона")',
  '"Высота базовой плоскости выхода" = ("Проекция оси выхода" * cos("Угол наклона") - 360мм) / sin("Угол наклона")',
  '"D1@Расстояние30" = "Проекция оси выхода"',
  '"D1@Расстояние31" = "Высота базовой плоскости выхода"',
  f'"{plane}" = "Высота базовой плоскости выхода"',
  f'"{sketch}" = ("Длина трубы" - "Отступ оси выхода от торца") * sin("Угол наклона")',
 ]
 mgr=tube.GetEquationMgr
 sw.ActivateDoc3(tube.GetPathName,False,2,e);assert not e.value
 assert not any('Отступ оси выхода от торца' in mgr.Equation(i) for i in range(mgr.GetCount))
 for expression in expressions:
  i=mgr.Add2(-1,expression,True);assert i>=0,expression;added.append(i)
 mgr.EvaluateAll
 cut=pipe_part.FeatureByName('Вырез-Вытянуть8');data=cut.GetDefinition
 null=w.VARIANT(pythoncom.VT_DISPATCH,None)
 sw.ActivateDoc3(pipe_part.GetPathName,False,2,e);assert not e.value
 assert data.AccessSelections(pipe_part,null)
 cut_original=(data.GetEndCondition(True),data.GetDepth(True),data.GetReverseOffset(True),data.GetTranslateSurface(True))
 data.SetEndCondition(True,0);data.SetDepth(True,.2)
 assert cut.ModifyDefinition(data,pipe_part,null)
 sw.ActivateDoc3(tube.GetPathName,False,2,e);assert not e.value
 print('Dependencies added, station/offset mm:',station*1000,offset,flush=True)
 assert tube.ForceRebuild3(False)
 assert abs(ear_part.Parameter('D7@Эскиз1').SystemValue-.024)<1e-8
 assert abs(tube.Parameter('D1@Расстояние30').SystemValue-2.06)<1e-8
 assert abs(pipe_part.Parameter('D2@Эскиз13').SystemValue-station*math.cos(alpha))<1e-8
 sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value;assert top.ForceRebuild3(False)
 issues=bridge.model_issues(sw,top);intersections=bridge.interference_issues(top)
 print('Baseline issues:',issues,'intersections:',intersections,flush=True)
 assert issues==(0,0,[]) and not intersections
 assert top.Save3(13,e,q) and not e.value
 result={'backup':str(backup),'expressions':expressions,'upper_station_mm':station*1000,'offset_mm':offset,'upper_cut_end':'Blind depth matching port extrusion (200 mm)','issues':issues,'interferences':intersections,'geometry':bridge.measured_geometry(top)}
 (base/'rebuild_dependency_fix_20261005.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Native dependencies saved and verified',flush=True)
except Exception:
 if added:
  sw.ActivateDoc3(tube.GetPathName,False,2,e)
  for i in reversed(added):mgr.Delete(i)
  for dimension,value in dimension_originals:dimension.SystemValue=value
  if cut_original:
   sw.ActivateDoc3(pipe_part.GetPathName,False,2,e);data=cut.GetDefinition;assert data.AccessSelections(pipe_part,null)
   data.SetEndCondition(True,cut_original[0]);data.SetDepth(True,cut_original[1]);data.SetReverseOffset(True,cut_original[2]);data.SetTranslateSurface(True,cut_original[3]);assert cut.ModifyDefinition(data,pipe_part,null)
  sw.ActivateDoc3(tube.GetPathName,False,2,e)
  mgr.EvaluateAll;tube.ForceRebuild3(False)
  sw.ActivateDoc3(top.GetPathName,False,2,e);top.ForceRebuild3(False)
  assert bridge.model_issues(sw,top)==(0,0,[]) and not bridge.interference_issues(top)
  assert top.Save3(13,e,q) and not e.value
  print('Restored saved baseline',flush=True)
 raise
finally:sw.CommandInProgress=previous
