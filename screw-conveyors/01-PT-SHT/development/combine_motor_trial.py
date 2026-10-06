from pathlib import Path
import pythoncom,win32com.client as w
sw=w.GetActiveObject('SldWorks.Application');path=Path('work/conditional_drive_trial/Мотор-редуктор — контроль.SLDPRT').resolve();d=sw.GetOpenDocumentByName(str(path))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(d.GetTitle,False,2,e)
cfg='Сборочная — резьба условно';d.ShowConfiguration2(cfg);created=[]
for step in range(20):
 bodies=list(d.GetBodies2(0,True));pair=None
 for i,a in enumerate(bodies):
  for b in bodies[i+1:]:
   aa=a.Copy();bb=b.Copy();err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
   results=aa.Operations2(15901,bb,0)
   if isinstance(results,tuple) and len(results)==2 and isinstance(results[1],int):results=results[0]
   volume=sum(w.Dispatch(x).GetMassProperties(1)[3] for x in results or [])
   if volume>1e-12:pair=(a,b,volume);break
  if pair:break
 if not pair:break
 a,b,volume=pair;print('merge',step,a.Name,b.Name,volume*1e9,flush=True)
 f=d.FeatureManager.InsertCombineFeature(15903,w.VARIANT(pythoncom.VT_DISPATCH,None),w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[a,b]));assert f and not f.GetErrorCode
 f.Name=f'Сборочная оболочка — объединение {step+1}';created.append(f)
 assert f.SetSuppression2(0,2,None);assert f.SetSuppression2(1,3,w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_BSTR,[cfg]))
 print('bodies',len(d.GetBodies2(0,True)),flush=True)
assert step<19
assert d.Save3(1,e,q);print('saved motor envelope',len(created),'bodies',len(d.GetBodies2(0,True)),flush=True)
