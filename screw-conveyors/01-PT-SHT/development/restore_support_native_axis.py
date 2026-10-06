exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
old=next(m for m in mates(support) if m.Name=='Расстояние8');ent=old.GetSpecificFeature2.MateEntity(0);part=ent.ReferenceComponent.GetModelDoc2
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(part.GetTitle,False,2,e)
face=next(f for b in part.GetBodies2(0,True) for f in b.GetFaces() if f.GetSurface.IsCylinder)
part.ClearSelection2(True);sel=part.SelectionManager.CreateSelectData;face.Select4(False,sel)
print('axis',part.InsertAxis2(True),flush=True)
f=part.FirstFeature
axes=[]
while f:
 if f.GetTypeName2=='RefAxis':axes.append(f)
 f=f.GetNextFeature
axis=axes[-1];axis.Name='Ось отверстия пластины — восстановлено'
q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);print('partsave',part.Save3(1,e,q),e.value,q.value,flush=True)
sw.ActivateDoc3(support.GetTitle,False,2,e)
for old in list(mates(support)):
 if old.Name not in ['Расстояние8','Расстояние9']:continue
 old.SetSuppression2(0,1,None);comp=old.GetSpecificFeature2.MateEntity(0).ReferenceComponent
 support.ClearSelection2(True)
 selection_name=axis.Name+'@'+comp.Name2+'@'+support.GetTitle.removesuffix('.SLDASM')
 print(selection_name,'select',support.Extension.SelectByID2(selection_name,'AXIS',0.,0.,0.,False,1,w.VARIANT(pythoncom.VT_DISPATCH,None),0),flush=True)
 ref=old.GetDefinition.EntitiesToMate[1]
 print('ref',ref.Select2(True,1),flush=True)
 data=support.CreateMateData(5);data.IsAdvancedMate=False;data.Distance=.05;data.MateAlignment=2;data.FlipDimension=True
 new=support.CreateMate(data);print('created',new,'error',new.GetErrorCode if new else None,flush=True)
 if not new or new.GetErrorCode:raise RuntimeError('Distance creation failed')
 name=old.Name;support.ClearSelection2(True);old.Select2(False,0);support.Extension.DeleteSelection2(0);new.Name=name+' — восстановлено'
print('save',support.Save3(1,e,q),e.value,q.value,flush=True)
doc.ForceRebuild3(False);print('top save',doc.Save3(1,e,q),e.value,q.value,flush=True)
