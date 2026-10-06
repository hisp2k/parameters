exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
cfg='Сборочная — резьба условно';root=Path('work/conditional_drive_trial').resolve();root.mkdir(exist_ok=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
for key,r,target in [('Вал шнека верхний',.0051,.006025),('Мотор-редуктор',.0033235,.004025),('Кран шаровый',None,None)]:
 src=next(c.GetModelDoc2 for c in doc.GetComponents(False) if key in c.Name2);path=root/(key+' — контроль.SLDPRT')
 sw.ActivateDoc3(src.GetTitle,False,2,e)
 if not path.exists():assert src.Extension.SaveAs2(str(path),0,3,w.VARIANT(pythoncom.VT_DISPATCH,None),'',False,e,q)
 spec=sw.GetOpenDocSpec(str(path));spec.DocumentType=1;spec.Silent=True;d=sw.OpenDoc7(spec);sw.ActivateDoc3(d.GetTitle,False,2,e)
 if cfg not in list(d.GetConfigurationNames):assert d.ConfigurationManager.AddConfiguration2(cfg,'Условное изображение резьбовых отверстий, исходная конфигурация сохранена.','',0,'','Сборочное представление',True)
 d.ShowConfiguration2(cfg)
 cylinders=[f for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder]
 print(key,'cylinders',[(round(f.GetSurface.CylinderParams[6]*1000,4),list(f.GetBox)) for f in cylinders if r is None or abs(f.GetSurface.CylinderParams[6]-r)<1e-6],flush=True)
 if r is not None:
  fs=[f for f in cylinders if abs(f.GetSurface.CylinderParams[6]-r)<1e-6];assert fs
  d.ClearSelection2(True);sel=d.SelectionManager.CreateSelectData;sel.Mark=1
  for i,f in enumerate(fs):assert f.Select4(i>0,sel)
  feature=d.FeatureManager.InsertMoveFace3(0,True,0.,target-r,None,None,0,0.)
  print('offset feature',feature.Name if feature else None,feature.GetErrorCode if feature else None,flush=True)
  if feature:
   feature.Name='Условная геометрия резьбовых отверстий'
   assert feature.SetSuppression2(0,2,None);assert feature.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
   print('radii after',sorted(set(round(f.GetSurface.CylinderParams[6]*1000,5) for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder)),flush=True)
 if key=='Мотор-редуктор':
  bodies=list(d.GetBodies2(0,True));feature=d.FeatureManager.InsertCombineFeature(15903,w.VARIANT(pythoncom.VT_DISPATCH,None),w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,bodies))
  print('combine',feature.Name if feature else None,'bodies',len(d.GetBodies2(0,True)),flush=True)
  if feature:
   feature.Name='Сборочная оболочка каталожной модели'
   assert feature.SetSuppression2(0,2,None);assert feature.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
 assert d.Save3(1,e,q)
