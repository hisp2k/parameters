import win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application')
d=s.NewDocument(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot',0,0,0)
print('active',d.GetTitle,flush=True)
f=d.FirstFeature;plane=None
while f:
 if f.Name=='Сверху':plane=f;break
 f=f.GetNextFeature
print('plane',plane.Name,plane.Select2(False,0),flush=True)
d.SketchManager.InsertSketch(True)
seg=d.SketchManager.CreateCircleByRadius(0,0,0,0.09)
print('circle',bool(seg),flush=True)
d.SketchManager.InsertSketch(True)
feat=d.FeatureManager.FeatureExtrusion2(True,False,False,0,0,0.005,0,False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
print('extruded',bool(feat),d.GetPartBox(True),flush=True)
p=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_крышка_нижняя.SLDPRT'
print('save',d.SaveAs3(str(p),0,0),flush=True)
