exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
for old in list(mates(support)):
 if old.Name not in ['Расстояние8','Расстояние9']:continue
 ent=old.GetSpecificFeature2.MateEntity(0);face=ent.ReferenceComponent.GetCorrespondingEntity(plane_candidates(ent)[0][1]);ref=old.GetDefinition.EntitiesToMate[1]
 for a in ['GetTypeName2','GetRefAxisParams','GetSpecificFeature2']:
  try:print(a,getattr(ref,a),flush=True)
  except Exception:pass
 old.SetSuppression2(0,1,None)
 support.ClearSelection2(True);sel=support.SelectionManager.CreateSelectData;sel.Mark=1
 print('select',face.Select4(False,sel),flush=True)
 try:print('refselect',ref.Select4(True,sel),flush=True)
 except Exception as ex:print(ex,flush=True)
 data=support.CreateMateData(5);data.IsAdvancedMate=False;data.Distance=.05;data.MateAlignment=2;data.FlipDimension=True
 new=support.CreateMate(data);print('new',new,flush=True)
 if new is None:
  try:ref=ref.GetSpecificFeature2
  except Exception:pass
  data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,[face,ref]);new=support.CreateMate(data);print('explicit new',new,flush=True)
 if new is None:old.SetSuppression2(1,1,None);continue
 print('err',new.GetErrorCode,flush=True)
 if new.GetErrorCode:raise RuntimeError('Mate error')
 name=old.Name;support.ClearSelection2(True);old.Select2(False,0);support.Extension.DeleteSelection2(0);new.Name=name+' — восстановлено'
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);print('save',support.Save3(1,e,q),e.value,q.value,flush=True)
