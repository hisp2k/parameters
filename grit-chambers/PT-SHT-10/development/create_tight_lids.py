from pathlib import Path
import win32com.client as w
s=w.Dispatch('SldWorks.Application')
t=r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot'
base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'
for name,plane,radius in [('CFD_inlet_lid.SLDPRT','Спереди',0.02551),('CFD_outlet_lid.SLDPRT','Спереди',0.03501),('CFD_bottom_lid.SLDPRT','Сверху',0.05101)]:
 d=s.NewDocument(t,0,0,0)
 f=d.FirstFeature
 while f and f.Name!=plane:f=f.GetNextFeature
 if not f:raise RuntimeError(plane)
 if not f.Select2(False,0):raise RuntimeError('plane select')
 d.SketchManager.InsertSketch(True)
 seg=d.SketchManager.CreateCircleByRadius(0,0,0,radius)
 d.SketchManager.InsertSketch(True)
 feat=d.FeatureManager.FeatureExtrusion2(True,False,False,0,0,0.005,0,False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
 if not feat:raise RuntimeError('extrude '+name)
 p=base/name;rc=d.SaveAs3(str(p),0,0)
 print(name,'radius',radius,'box',list(d.GetPartBox(True)),'savecode',rc,'bytes',p.stat().st_size,flush=True)
