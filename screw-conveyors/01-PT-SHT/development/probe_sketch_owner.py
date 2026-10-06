exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
f=doc.FirstFeature
while f and f.Name!='Эскиз1':f=f.GetNextFeature
sketch=f.GetSpecificFeature2
for rel in sketch.RelationManager.GetRelations(1) or []:
 for ent in rel.GetDefinitionEntities:
  try:print(ent.GetSketch.GetSketchFeature.Name,flush=True)
  except Exception as ex:print('err',str(ex),flush=True)
