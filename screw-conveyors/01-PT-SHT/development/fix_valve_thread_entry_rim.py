exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import sys;sys.path.insert(0,str(base));import bridge
cfg='Сборочная — резьба условно';d=next(c.GetModelDoc2 for c in doc.GetComponents(False) if 'Кран шаровый' in c.Name2);e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(d.GetPathName,False,2,e);d.ShowConfiguration2(cfg)
for label,offset,flip in [('левый',.00445,True),('правый',.03955,False)]:
 d.ClearSelection2(True);assert d.FeatureByName('Right').Select2(False,0);sk=d.SketchManager;sk.InsertSketch(True);sk.AddToDB=True;sk.CreateCircleByRadius(0.,0.,0.,.010675);sk.AddToDB=False;sk.InsertSketch(True)
 f=d.FeatureManager.FeatureCut4(False,False,False,0,0,.0045,.0045,False,False,False,False,0.,0.,False,False,False,False,False,False,True,False,False,False,3,offset,flip,True);assert f and not f.GetErrorCode;f.Name=f'Условная резьба G1_2 — входная кромка {label}';assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
assert any(abs(f.GetSurface.CylinderParams[6]-.0093)<1e-8 for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder);assert d.Save3(9,e,q)
for path in bridge.FILES.values():
 sub=sw.GetOpenDocumentByName(str(path));sw.ActivateDoc3(sub.GetPathName,False,2,e);sub.ForceRebuild3(False)
sw.ActivateDoc3(doc.GetPathName,False,2,e);doc.ForceRebuild3(False);assert doc.Save3(13,e,q);print('valve entry representation fixed; internal bore and seating unchanged',flush=True)
