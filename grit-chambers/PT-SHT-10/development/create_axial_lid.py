import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application');d=s.ActiveDoc
print('active',d.GetTitle,flush=True)
plane=None;f=d.FirstFeature
while f:
 if f.Name=='Спереди':plane=f;break
 f=f.GetNextFeature
print('plane',plane.Name,'selected',plane.Select2(False,0),flush=True)
d.SketchManager.InsertSketch(True)
seg=d.SketchManager.CreateCircleByRadius(0.0,0.0,0.0,0.10)
print('circle',bool(seg),flush=True)
d.SketchManager.InsertSketch(True)
print('extruding',flush=True)
feat=d.FeatureManager.FeatureExtrusion2(True,False,False,0,0,0.005,0.0,False,False,False,False,0.0,0.0,False,False,False,False,True,True,True,0,0.0,False)
print('extruded',bool(feat),feat.Name if feat else None,flush=True)
print('box',d.GetPartBox(True),flush=True)
path=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_крышка_боковая.SLDPRT'
print('save',d.SaveAs3(str(path),0,0),path,flush=True)
