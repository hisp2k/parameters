exec(open('work/assemble_lower_candidate.py',encoding='utf-8').read().split('oldseal=next')[0])
for f in mates():
 if f.GetErrorCode:
  print(f.Name,f.GetTypeName2,f.GetErrorCode)
  for i in (0,1):
   ent=f.GetSpecificFeature2.MateEntity(i);c=ent.ReferenceComponent
   print(i,c.Name2,'ref',ent.Reference,'params',list(ent.EntityParams or []))
   if ent.Reference is None:
    for body in c.GetModelDoc2.GetBodies2(0,True):
     for face in body.GetFaces():
      if face.GetSurface.IsPlane:print('plane',list(face.GetSurface.PlaneParams),'box',list(face.GetBox))
