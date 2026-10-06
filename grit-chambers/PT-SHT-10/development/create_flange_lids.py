from pathlib import Path
import win32com.client as w
s=w.Dispatch('SldWorks.Application');base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель';t=r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot'
for name,plane,radius in [('CFD_inlet_flange_lid.SLDPRT','Спереди',0.02951),('CFD_outlet_flange_lid.SLDPRT','Спереди',0.03901),('CFD_bottom_flange_lid.SLDPRT','Сверху',0.05501)]:
 d=s.NewDocument(t,0,0,0);f=d.FirstFeature
 while f and f.Name!=plane:f=f.GetNextFeature
 if not f or not f.Select2(False,0):raise RuntimeError('plane')
 d.SketchManager.InsertSketch(True);seg=d.SketchManager.CreateCircleByRadius(0,0,0,radius);d.SketchManager.InsertSketch(True)
 feat=d.FeatureManager.FeatureExtrusion2(True,False,False,0,0,0.005,0,False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
 if not feat:raise RuntimeError('extrude')
 path=base/name;d.SaveAs3(str(path),0,0)
 print(name,'r',radius,'box',list(d.GetPartBox(True)),'bytes',path.stat().st_size,flush=True)
