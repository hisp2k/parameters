from pathlib import Path
import win32com.client as w
s=w.Dispatch('SldWorks.Application');t=r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot';base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'
for name,plane,rin,rout,depth in [('CFD_inlet_joint_seal_v2.SLDPRT','Спереди',0.0284,0.0296,0.010),('CFD_outlet_joint_seal_v2.SLDPRT','Спереди',0.0379,0.0391,0.011),('CFD_bottom_joint_seal_v2.SLDPRT','Сверху',0.0539,0.0551,0.006)]:
 d=s.NewDocument(t,0,0,0);f=d.FirstFeature
 while f and f.Name!=plane:f=f.GetNextFeature
 d.ClearSelection2(True)
 if not f or not f.Select2(False,0):raise RuntimeError('plane '+name)
 sm=d.SketchManager;sm.InsertSketch(True)
 sm.AddToDB=True
 try:
  a=sm.CreateCircleByRadius(0,0,0,rout);b=sm.CreateCircleByRadius(0,0,0,rin)
 finally:sm.AddToDB=False
 print(name,'radii',a.GetCurve.CircleParams[6],b.GetCurve.CircleParams[6],flush=True)
 sm.InsertSketch(True)
 feat=d.FeatureManager.FeatureExtrusion2(True,False,False,0,0,depth,0,False,False,False,False,0,0,False,False,False,False,True,True,True,0,0,False)
 if not feat:raise RuntimeError('extrude '+name)
 p=base/name;d.SaveAs3(str(p),0,0)
 print(' box',list(d.GetPartBox(True)),'bytes',p.stat().st_size,flush=True)
