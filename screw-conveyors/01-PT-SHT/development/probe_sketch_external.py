exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
f=doc.FirstFeature
while f:
 if f.Name=='Эскиз1':break
 f=f.GetNextFeature
sketch=f.GetSpecificFeature2;mgr=sketch.RelationManager
for filter in [1,3,6]:
 relations=mgr.GetRelations(filter) or []
 print('FILTER',filter,len(relations),flush=True)
 for rel in relations:
  print('type',rel.GetRelationType,flush=True)
  for a in ['GetDefinitionEntities','GetEntities','GetEntitiesType']:
   try:print(a,getattr(rel,a),flush=True)
   except Exception:pass
  for ent in rel.GetEntities or []:
   for a in ['X','Y','Z','GetStartPoint2','GetEndPoint2','GetCurve','GetType']:
    try:print(a,getattr(ent,a),flush=True)
    except Exception:pass
