from pathlib import Path
import sys,win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base));import bridge
sw=w.GetActiveObject('SldWorks.Application');prev=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY));part=next(c.GetModelDoc2 for c in top.GetComponents(False) if 'Труба шнека' in c.Name2)
 for name in ['Эскиз13','Эскиз10']:
  sketch=part.FeatureByName(name).GetSpecificFeature2
  print(name,'transform',list(sketch.ModelToSketchTransform.ArrayData),flush=True)
  for s in sketch.GetSketchSegments or []:
   print('segment',s.GetType,'length',s.GetLength,'radius',s.GetRadius if s.GetType==1 else None,flush=True)
   if s.GetType==1:
    cp=s.GetCenterPoint2;p=[cp.X,cp.Y,cp.Z];t=list(sketch.ModelToSketchTransform.Inverse.ArrayData);mp=[sum(p[j]*t[j*3+k] for j in range(3))+t[9+k] for k in range(3)];print('center sketch',p,'model',mp,flush=True)
 for name in ['Плоскость5','Плоскость6']:
  f=part.FeatureByName(name);print(name,'parents',[(p.Name,p.GetTypeName2) for p in f.GetParents or []],'transform',list(f.GetSpecificFeature2.Transform.ArrayData),flush=True)
 for c in top.GetComponents(False):
  if 'Патрубок шнека' not in c.Name2:continue
  d=c.GetModelDoc2;t=list(c.Transform2.ArrayData)
  for b in d.GetBodies2(0,True):
   for face in b.GetFaces():
    sf=face.GetSurface
    if sf.IsCylinder and abs(sf.CylinderParams[6]-.05)<1e-6:
     q=list(sf.CylinderParams);print('port axis',[sum(q[j+3]*t[j*3+i] for j in range(3)) for i in range(3)],flush=True);break
 print('pipe box',part.GetPartBox(True),flush=True)
 for b in part.GetBodies2(0,True):
  for face in b.GetFaces():
   sf=face.GetSurface
   if sf.IsCylinder and abs(sf.CylinderParams[6]-.0705)<1e-6:print('native pipe axis',list(sf.CylinderParams),flush=True);break
finally:sw.CommandInProgress=prev

