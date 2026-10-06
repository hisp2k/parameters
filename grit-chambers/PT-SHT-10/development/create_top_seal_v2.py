from pathlib import Path
import win32com.client as w
s=w.Dispatch('SldWorks.Application');d=s.ActiveDoc;print('active',d.GetTitle)
f=d.FirstFeature
while f and f.Name!='Сверху':f=f.GetNextFeature
assert f
d.ClearSelection2(True)
assert f.Select2(False,0)
d.SketchManager.InsertSketch(True)
a=d.SketchManager.CreateCircleByRadius(0,0,0,0.301)
b=d.SketchManager.CreateCircleByRadius(0,0,0,0.289)
d.SketchManager.InsertSketch(True)
feat=d.FeatureManager.FeatureExtrusion2(True,False,False,0,0,0.0012,0,False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
print('feat',bool(feat),'box',d.GetPartBox(True),flush=True)
p=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_top_seal_v2.SLDPRT';print('save',d.SaveAs3(str(p),0,0),'bytes',p.stat().st_size,flush=True)
