exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import shutil
cfg='Сборочная — резьба условно';e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
components=[(c.Name2,c) for c in doc.GetComponents(False)];d=next(c.GetModelDoc2 for n,c in components if 'Кран шаровый' in n)
backup=base/'snapshots/20261004-before-valve-ring-fix';backup.mkdir(parents=True,exist_ok=True);shutil.copy2(d.GetPathName,backup/Path(d.GetPathName).name)
sw.ActivateDoc3(d.GetTitle,False,2,e)
if cfg not in list(d.GetConfigurationNames):assert d.ConfigurationManager.AddConfiguration2(cfg,'Условные резьбовые зоны G1/2 на концах; центральный проход сохранён.','',0,'','Сборочное изображение; не размеры изготовления крана',True)
d.ShowConfiguration2(cfg)
for label,offset,flip in [('левый',.00045,True),('правый',.03555,False)]:
 d.ClearSelection2(True);assert d.FeatureByName('Right').Select2(False,0)
 sk=d.SketchManager;sk.InsertSketch(True);sk.AddToDB=True;sk.CreateCircleByRadius(0.,0.,0.,.010675);sk.AddToDB=False;sk.InsertSketch(True)
 f=d.FeatureManager.FeatureCut4(False,False,False,0,0,.0065,.0065,False,False,False,False,0.,0.,False,False,False,False,False,False,True,False,False,False,3,offset,flip,True);assert f and not f.GetErrorCode;f.Name=f'Условная резьба G1_2 — {label} конец';assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
assert any(abs(f.GetSurface.CylinderParams[6]-.0093)<1e-8 for b in d.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder);assert d.Save3(1,e,q);parts={d.GetPathName:d}
exec(open('work/thread_parent_repair.py',encoding='utf-8').read())
shaft=next(c.GetModelDoc2 for n,c in components if 'Вал шнека нижний' in n);shutil.copy2(shaft.GetPathName,backup/Path(shaft.GetPathName).name)
sw.ActivateDoc3(shaft.GetTitle,False,2,e);shaft.Parameter('D1@Плоскость2').SystemValue=.004225;shaft.ForceRebuild3(False);assert shaft.Save3(1,e,q)
sw.ActivateDoc3(doc.GetTitle,False,2,e);doc.ForceRebuild3(False);assert doc.Save3(1,e,q);print('valves and lower ring fixed',flush=True)
