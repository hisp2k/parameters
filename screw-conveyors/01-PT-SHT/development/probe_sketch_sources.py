exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
f=doc.FirstFeature
while f and f.Name!='Эскиз1':f=f.GetNextFeature
print('children',f.GetChildren,flush=True)
sketch=f.GetSpecificFeature2
for rel in sketch.RelationManager.GetRelations(1) or []:
 print('REL',rel.GetRelationType,flush=True)
 for ent in rel.GetDefinitionEntities or []:
  for attr in ['GetID','GetSketch','GetComponent','GetName']:
   try:
    obj=getattr(ent,attr)
    print(attr,obj,flush=True)
    if attr=='GetSketch':print('sketchfeature',obj.GetFeature.Name,flush=True)
   except Exception:pass
  try:
   a=ent.GetStartPoint2;b=ent.GetEndPoint2;print('line',a.X,a.Y,a.Z,b.X,b.Y,b.Z,flush=True)
  except Exception:pass
