exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
import shutil,sys
sys.path.insert(0,str(base));import bridge
p=bridge.FILES['tube'];d=sw.GetOpenDocumentByName(str(p));backup=base/'snapshots/20261004-before-remove-sbrosivatel';backup.mkdir(parents=True,exist_ok=True)
for file in [p,path,base/'state.json',base/'index.html',base/'bridge.py']:
 
 if not (backup/file.name).exists():shutil.copy2(file,backup/file.name)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
sw.ActivateDoc3(d.GetTitle,False,2,e);assert sw.ActiveDoc.GetPathName==str(p)
target=[c for c in d.GetComponents(False) if 'Сбрасыватель' in c.Name2];assert len(target)==1
mgr=d.GetEquationMgr
removed=[]
for i in range(mgr.GetCount-1,-1,-1):
 expr=mgr.Equation(i)
 if any(x in expr for x in ["Сбрасыватель", "Толщина стенки сбрасывателя", "Длина сбрасывателя", "D1@Расстояние26", "D1@Расстояние27"]):
  removed.append(expr);mgr.Delete(i);assert expr not in [mgr.Equation(j) for j in range(mgr.GetCount)]
for i in range(mgr.GetCount):
 expr=mgr.Equation(i)
 if 'Диаметр сбрасывателя' in expr:bridge.set_equation(mgr,i,expr.replace('Диаметр сбрасывателя','Диаметр отверстия корпуса'))
for name in ['Совпадение52','Расстояние26','Расстояние27']:
 d.ClearSelection2(True);f=d.FeatureByName(name);assert f and f.Select2(False,0);assert d.Extension.DeleteSelection2(0)
d.ClearSelection2(True);sd=d.SelectionManager.CreateSelectData;assert target[0].Select4(False,sd,False);assert d.Extension.DeleteSelection2(0)
assert not any('Сбрасыватель' in c.Name2 for c in d.GetComponents(False))
d.ForceRebuild3(False);assert not [(m.Name,m.GetErrorCode) for m in mates(d) if m.GetErrorCode]
assert d.Save3(1,e,q);print('tube saved',e.value,q.value,flush=True)
sw.ActivateDoc3(doc.GetTitle,False,2,e);doc.ForceRebuild3(False)
assert not any('Сбрасыватель' in c.Name2 for c in doc.GetComponents(False));assert not [(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode]
assert doc.Save3(1,e,q)
report={'removed_component':target[0].Name2 if False else "PT.SHT.01.21.00.07 'Сбрасыватель'",'removed_equations':removed,'removed_mates':['Совпадение52','Расстояние26','Расстояние27'],'hole_retained':True,'opening_diameter_mm':110,'component_count':len(doc.GetComponents(False)),'mate_errors':0}
(base/'sbrosivatel_removal_20261004.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(report,flush=True)
