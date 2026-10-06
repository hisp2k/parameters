from pathlib import Path
import sys,json
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sys.path.insert(0,str(base))
import bridge
sw=w.GetActiveObject('SldWorks.Application')
previous=sw.CommandInProgress;sw.CommandInProgress=True
try:
 top=sw.GetOpenDocumentByName(str(bridge.TOP_ASSEMBLY))
 for keyword in ('Ухо','Труба шнека'):
  component=next(c for c in top.GetComponents(False) if keyword in c.Name2)
  part=component.GetModelDoc2
  print('PART',part.GetPathName,'dirty',part.GetSaveFlag,'box',part.GetPartBox(True),flush=True)
  mgr=part.GetEquationMgr
  print('equations',[mgr.Equation(i) for i in range(mgr.GetCount)],flush=True)
  feature=part.FirstFeature
  while feature:
   name=feature.Name;kind=feature.GetTypeName2
   dimensions=[];display=feature.GetFirstDisplayDimension
   while display:
    dim=display.GetDimension2(0);dimensions.append((dim.FullName,float(dim.SystemValue)))
    display=feature.GetNextDisplayDimension(display)
   print('feature',name,kind,'error',feature.GetErrorCode,'dims',dimensions,flush=True)
   if kind=='ProfileFeature' and keyword=='Ухо':
    sketch=feature.GetSpecificFeature2
    for segment in sketch.GetSketchSegments or []:
     if segment.GetType==0:
      a=segment.GetStartPoint2;b=segment.GetEndPoint2
      print('line',(a.X,a.Y,a.Z),(b.X,b.Y,b.Z),flush=True)
     elif segment.GetType==1:
      point=segment.GetCenterPoint2;print('arc',(point.X,point.Y,point.Z),segment.GetRadius,flush=True)
   feature=feature.GetNextFeature
 print('baseline',bridge.measured_geometry(top),'issues',bridge.model_issues(sw,top),flush=True)
finally:sw.CommandInProgress=previous
