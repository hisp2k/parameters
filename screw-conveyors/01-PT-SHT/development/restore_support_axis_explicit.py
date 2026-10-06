exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(support.GetTitle,False,2,e)
for old in list(mates(support)):
 if old.Name not in ['Расстояние8','Расстояние9']:continue
 old.SetSuppression2(0,1,None);comp=old.GetSpecificFeature2.MateEntity(0).ReferenceComponent
 support.ClearSelection2(True)
 name='Ось отверстия пластины — восстановлено@'+comp.Name2+'@'+support.GetTitle.removesuffix('.SLDASM')
 if not support.Extension.SelectByID2(name,'AXIS',0.,0.,0.,False,1,w.VARIANT(pythoncom.VT_DISPATCH,None),0):raise RuntimeError('Axis select failed')
 axis=support.SelectionManager.GetSelectedObject6(1,1)
 try:axis=axis.GetSpecificFeature2
 except Exception:pass
 plane=old.GetDefinition.EntitiesToMate[1].GetSpecificFeature2
 data=support.CreateMateData(5);data.IsAdvancedMate=False;data.Distance=.05;data.MateAlignment=2;data.FlipDimension=True;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[axis,plane])
 new=support.CreateMate(data);print('created',new,'err',new.GetErrorCode if new else None,flush=True)
 if not new or new.GetErrorCode:raise RuntimeError('Creation failed')
 name=old.Name;support.ClearSelection2(True);old.Select2(False,0);support.Extension.DeleteSelection2(0);new.Name=name+' — восстановлено'
print('support save',support.Save3(1,e,q),e.value,q.value,flush=True);doc.ForceRebuild3(False);print('top save',doc.Save3(1,e,q),e.value,q.value,flush=True)
