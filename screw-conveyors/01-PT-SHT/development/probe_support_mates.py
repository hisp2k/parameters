exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
for m in mates(support):
 if not m.GetErrorCode:continue
 print(m.Name,m.GetTypeName2)
 for i in (0,1):
  ent=m.GetSpecificFeature2.MateEntity(i)
  if ent.Reference is None:
   print(i,ent.ReferenceComponent.Name2,'planes',[(round(d*1000,3),round(dot,4),round(area*1e6,1)) for d,f,dot,area in plane_candidates(ent)])
   part=ent.ReferenceComponent.GetModelDoc2
   for body in part.GetBodies2(0,True):print('bodybox',body.GetBodyBox)
 print('specific alignment',m.GetSpecificFeature2.Alignment,flush=True)
 print('definition')
 for attr in ['Distance','MateAlignment','FlipDimension','IsAdvancedMate','MinimumDistance','MaximumDistance']:
  try:print(attr,getattr(m.GetDefinition,attr))
  except Exception:pass

