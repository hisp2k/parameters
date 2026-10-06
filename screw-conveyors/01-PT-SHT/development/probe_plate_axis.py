exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
for m in list(mates(support)):
 if m.GetErrorCode==47:support.ClearSelection2(True);m.Select2(False,0);support.Extension.DeleteSelection2(0)
old=next(m for m in mates(support) if m.Name=='Расстояние8');old.SetSuppression2(1,1,None)
ent=old.GetSpecificFeature2.MateEntity(0);c=ent.ReferenceComponent;p=list(ent.EntityParams);t=list(c.Transform2.ArrayData);local=[sum((p[i]-t[9+i])*t[j*3+i] for i in range(3)) for j in range(3)]
print('local axispoint',local,flush=True)
for body in c.GetModelDoc2.GetBodies2(0,True):
 for face in body.GetFaces():
  if face.GetSurface.IsCylinder:print('cylinder',list(face.GetSurface.CylinderParams),flush=True)
