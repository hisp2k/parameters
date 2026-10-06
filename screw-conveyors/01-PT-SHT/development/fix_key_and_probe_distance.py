exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
old=next(m for m in mates(doc) if m.Name=='Концентричный85')
new=next(m for m in mates(doc) if m.GetTypeName2=='MateConcentric' and not m.IsSuppressed and any('Шпонка' in m.GetSpecificFeature2.MateEntity(i).ReferenceComponent.Name2 for i in (0,1)))
doc.ClearSelection2(True);old.Select2(False,0);doc.Extension.DeleteSelection2(0);new.Name='Концентричный85 — восстановлено'
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);print(doc.Save3(1,e,q),e.value,q.value)
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
for m in mates(support):
 if not m.GetErrorCode:continue
 definition=m.GetDefinition
 print(m.Name,'Access',definition.AccessSelections(support,None),flush=True)
 try:
  print('alignment',definition.MateAlignment,'specific',m.GetSpecificFeature2.Alignment,flush=True)
 except Exception as ex:print(str(ex),flush=True)
 definition.ReleaseSelectionAccess()
