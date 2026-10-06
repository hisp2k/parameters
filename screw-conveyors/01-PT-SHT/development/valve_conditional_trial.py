from pathlib import Path
import pythoncom,win32com.client as w
sw=w.GetActiveObject('SldWorks.Application');path=Path('work/conditional_drive_trial/Кран шаровый — контроль.SLDPRT').resolve();d=sw.GetOpenDocumentByName(str(path));cfg='Сборочная — резьба условно'
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(d.GetTitle,False,2,e);d.ShowConfiguration2(cfg)
for label,offset,flip in [('левый',.00045,True),('правый',.03555,False)]:
 d.ClearSelection2(True);assert d.FeatureByName('Right').Select2(False,0)
 sk=d.SketchManager;sk.InsertSketch(True);sk.AddToDB=True;sk.CreateCircleByRadius(0.,0.,0.,.010675);sk.AddToDB=False;sk.InsertSketch(True)
 f=d.FeatureManager.FeatureCut4(False,False,False,0,0,.0065,.0065,False,False,False,False,0.,0.,False,False,False,False,False,False,True,False,False,False,3,offset,flip,True)
 assert f and not f.GetErrorCode;f.Name=f'Условная резьба G1_2 — {label} конец'
 assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
 print('cut',label,flush=True)
d.ForceRebuild3(False);print('bore cylinders',[(f.GetSurface.CylinderParams[6]*1000,list(f.GetBox)) for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder and f.GetSurface.CylinderParams[6] in [.0093,.010675]],flush=True)
assert d.Save3(1,e,q);print('saved',flush=True)

