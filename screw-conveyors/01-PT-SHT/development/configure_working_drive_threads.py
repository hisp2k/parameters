exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import shutil
cfg='Сборочная — резьба условно';e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);parts={}
backup=base/'snapshots/20261004-before-conditional-drive';backup.mkdir(parents=True,exist_ok=True)
for key,r,target in [('Вал шнека верхний',.0051,.006025),('Мотор-редуктор',.0033235,.004025)]:
 d=next(c.GetModelDoc2 for c in doc.GetComponents(False) if key in c.Name2);parts[d.GetPathName]=d;p=Path(d.GetPathName)
 if not (backup/p.name).exists():shutil.copy2(p,backup/p.name)
 sw.ActivateDoc3(d.GetTitle,False,2,e)
 if cfg not in list(d.GetConfigurationNames):assert d.ConfigurationManager.AddConfiguration2(cfg,'Сборочное изображение резьбовых отверстий; исходная конфигурация сохранена.','',0,'','Не использовать условный просвет как размер сверления',True)
 d.ShowConfiguration2(cfg)
 if not d.FeatureByName('Условная геометрия резьбовых отверстий'):
  fs=[f for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder and abs(f.GetSurface.CylinderParams[6]-r)<1e-7];assert fs
  d.ClearSelection2(True);sel=d.SelectionManager.CreateSelectData;sel.Mark=1
  for i,f in enumerate(fs):assert f.Select4(i>0,sel)
  f=d.FeatureManager.InsertMoveFace3(0,True,0.,target-r,None,None,0,0.);assert f and not f.GetErrorCode;f.Name='Условная геометрия резьбовых отверстий';assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
 if key=='Мотор-редуктор':
  for step in range(20):
   bodies=list(d.GetBodies2(0,True));pair=None
   for i,a in enumerate(bodies):
    for b in bodies[i+1:]:
     result=a.Copy().Operations2(15901,b.Copy(),0)
     if isinstance(result,tuple) and len(result)==2 and isinstance(result[1],int):result=result[0]
     volume=sum(w.Dispatch(x).GetMassProperties(1)[3] for x in result or [])
     if volume>1e-12:pair=(a,b);break
    if pair:break
   if not pair:break
   f=d.FeatureManager.InsertCombineFeature(15903,w.VARIANT(pythoncom.VT_DISPATCH,None),w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,list(pair)));assert f and not f.GetErrorCode;f.Name=f'Сборочная оболочка — объединение {step+1}';assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]));print('motor merged',step+1,flush=True)
  assert step<19
 assert d.Save3(1,e,q);print('part saved',key,flush=True)
exec(open('work/thread_parent_repair.py',encoding='utf-8').read())
