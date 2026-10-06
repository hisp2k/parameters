exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
from math import dist
old=next(m for m in mates(doc) if m.Name=='Концентричный85');ents=[old.GetSpecificFeature2.MateEntity(i) for i in (0,1)];ent=ents[1];c=ent.ReferenceComponent;p=list(ent.EntityParams);t=list(c.Transform2.ArrayData);candidates=[]
for body in c.GetModelDoc2.GetBodies2(0,True):
 for face in body.GetFaces():
  if not face.GetSurface.IsCylinder:continue
  q=list(face.GetSurface.CylinderParams)
  if abs(q[6]-p[6])>1e-6:continue
  o=[sum(q[j]*t[j*3+i] for j in range(3))+t[9+i] for i in range(3)]
  delta=[o[i]-p[i] for i in range(3)];axial=sum(delta[i]*p[i+3] for i in range(3));perp=sum((delta[i]-axial*p[i+3])**2 for i in range(3))**.5
  candidates.append((perp,face))
print('candidates',[d*1000 for d,f in candidates],flush=True)
face=min(candidates,key=lambda a:a[0])[1];fs=[old.GetDefinition.EntitiesToMate[0],c.GetCorrespondingEntity(face)];alignment=old.GetDefinition.MateAlignment;before=tuple(c.Transform2.ArrayData[9:12]);old.SetSuppression2(0,1,None)
data=doc.CreateMateData(1);data.MateAlignment=alignment;data.EntitiesToMate=w.VARIANT(pythoncom.VT_ARRAY|pythoncom.VT_DISPATCH,fs)
new=doc.CreateMate(data)
if not new or new.GetErrorCode:raise RuntimeError('Key mate creation failed')
print('key movement',dist(before,c.Transform2.ArrayData[9:12])*1000,flush=True)
if dist(before,c.Transform2.ArrayData[9:12])>.001:raise RuntimeError('Unexpected key move')
doc.ClearSelection2(True);old.Select2(False,0);doc.Extension.DeleteSelection2(0);new.Name='Концентричный85 — восстановлено'
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);print('save',doc.Save3(1,e,q),e.value,q.value,flush=True)
