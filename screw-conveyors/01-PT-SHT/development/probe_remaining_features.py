exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
tube=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Труба в сборе' in c.Name2)
eq=tube.GetEquationMgr
print('equations',eq.GetCount,flush=True)
for i in range(eq.GetCount):print(i,eq.Equation(i),eq.Status,flush=True)
features=doc.FirstFeature
while features:
 if features.Name=='Эскиз1':
  sketch=features.GetSpecificFeature2;mgr=sketch.RelationManager
  print('sketch relations')
  for rel in mgr.GetRelations(0) or []:
   for attr in ['GetRelationType','GetStatus','GetEntities']:
    try:print(attr,getattr(rel,attr),flush=True)
    except Exception:pass
 features=features.GetNextFeature
print('components',len(doc.GetComponents(False)),flush=True)

