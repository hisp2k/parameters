from pathlib import Path
import sys,json,shutil,pythoncom,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));part=next(c.GetModelDoc2 for c in top.GetComponents(False) if 'Труба шнека' in c.Name2)
 backup=base/'snapshots/20261005-before-upper-port-cut-selection';assert not backup.exists()
 for p in {Path(c.GetPathName) for c in top.GetComponents(False) if c.GetPathName}|{bridge.TOP_ASSEMBLY}:
  if p.is_file() and p.is_relative_to(base):
   dest=backup/p.relative_to(base);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 sw.ActivateDoc3(part.GetPathName,False,2,e);assert not e.value
 before=sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True))
 f=part.FeatureByName('Вырез-Вытянуть8');data=f.GetDefinition
 null=w.VARIANT(pythoncom.VT_DISPATCH,None)
 assert data.AccessSelections(part,null)
 modified=False
 try:
  radius=part.Parameter('D1@Эскиз2').SystemValue/2-part.Parameter('D5@Вытянуть-Тонкостенный1').SystemValue
  faces=[face for b in part.GetBodies2(0,True) for face in b.GetFaces() if face.GetSurface.IsCylinder and abs(face.GetSurface.CylinderParams[6]-radius)<1e-7]
  face=max(faces,key=lambda f:f.GetArea)
  data.SetEndCondition(True,10);data.SetEndConditionReference(True,face);data.BothDirections=False
  modified=bool(f.ModifyDefinition(data,part,null));assert modified
 finally:
  if not modified:data.ReleaseSelectionAccess
 assert part.ForceRebuild3(False)
 after=sum(b.GetMassProperties(1)[3] for b in part.GetBodies2(0,True))
 sw.ActivateDoc3(top.GetPathName,False,2,e);assert not e.value;assert top.ForceRebuild3(False)
 assert bridge.model_issues(sw,top)==(0,0,[])
 assert not bridge.interference_issues(top)
 assert top.Save3(13,e,q) and not e.value
 (base/'upper_port_cut_fix_20261005.json').write_text(json.dumps({'feature':'Вырез-Вытянуть8','before':'Глубина 200 мм','after':'До внутренней цилиндрической поверхности трубы','volume_change_mm3':(after-before)*1e9,'retained_opening_diameter_mm':part.Parameter('D1@Эскиз10').SystemValue*1000,'backup':str(backup),'issues':0,'interferences':0},ensure_ascii=False,indent=2),encoding='utf-8')
 print('upper port cut: volume change mm3',(after-before)*1e9,'errors/intersections 0',flush=True)
finally:sw.CommandInProgress=prev

