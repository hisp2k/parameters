exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
src=next(c.GetModelDoc2 for c in doc.GetComponents(False) if 'Гайка М6' in c.Name2)
target=Path('work/thread_config_trial/Гайка М6 — контроль.SLDPRT').resolve();target.parent.mkdir(exist_ok=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(src.GetTitle,False,2,e)
if not target.exists():assert src.Extension.SaveAs2(str(target),0,3,w.VARIANT(pythoncom.VT_DISPATCH,None),'',False,e,q)
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=1;spec.Silent=True;d=sw.OpenDoc7(spec);sw.ActivateDoc3(d.GetTitle,False,2,e)
cfg='Сборочная — резьба условно';original=next(n for n in d.GetConfigurationNames if n!=cfg)
if cfg not in list(d.GetConfigurationNames):assert d.ConfigurationManager.AddConfiguration2(cfg,'Резьба М6 условно. Для контроля сборки, не для назначения размеров отверстия.','',0,'','Условная сборочная геометрия резьбы',True)
d.ShowConfiguration2(cfg);assert d.ConfigurationManager.ActiveConfiguration.Name==cfg
old=d.FeatureByName('Условная резьба М6 — сборочный просвет')
if old:
 d.ClearSelection2(True);assert old.Select2(False,0);assert d.Extension.DeleteSelection2(1)
faces=[f for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder]
print('radii',[f.GetSurface.CylinderParams[6]*1000 for f in faces],flush=True)
bore=min(faces,key=lambda f:f.GetSurface.CylinderParams[6]);r=bore.GetSurface.CylinderParams[6]
print('cylinder',list(bore.GetSurface.CylinderParams),flush=True)
axis=list(bore.GetSurface.CylinderParams[3:6]);k=max(range(3),key=lambda i:abs(axis[i]));plane=['Справа','Сверху','Спереди'][k]
d.ClearSelection2(True);assert d.FeatureByName(plane).Select2(False,0)
sk=d.SketchManager;sk.InsertSketch(True);sk.AddToDB=True;sk.CreateCircleByRadius(0.,0.,0.,.003025);sk.AddToDB=False;sk.InsertSketch(True)
f=d.FeatureManager.FeatureCut4(False,False,False,1,1,.1,.1,False,False,False,False,0.,0.,False,False,False,False,False,False,True,False,False,False,0,0.,False,True)
assert f and not f.GetErrorCode
f.Name='Условная резьба М6 — сборочный просвет'
print('new radii',sorted(set(round(face.GetSurface.CylinderParams[6]*1000,6) for b in d.GetBodies2(0,True) for face in b.GetFaces() if face.GetSurface.IsCylinder)),flush=True)
assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
d.ShowConfiguration2(original);assert d.ConfigurationManager.ActiveConfiguration.Name==original;print('original radii',sorted(set(round(face.GetSurface.CylinderParams[6]*1000,6) for b in d.GetBodies2(0,True) for face in b.GetFaces() if face.GetSurface.IsCylinder)),flush=True)
d.ShowConfiguration2(cfg);assert d.ConfigurationManager.ActiveConfiguration.Name==cfg;assert d.Save3(1,e,q);print('saved trial',flush=True)
