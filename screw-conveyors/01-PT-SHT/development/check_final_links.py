exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
doc.ForceRebuild3(False)
print('TOPMATES',[(m.Name,m.GetErrorCode) for m in mates(doc) if m.GetErrorCode],flush=True)
f=doc.FirstFeature
while f:
 if f.GetErrorCode and f.GetTypeName2!='MateGroup':
  print('feature',f.Name,f.GetTypeName2,f.GetErrorCode,flush=True)
  if f.GetTypeName2=='ProfileFeature':
   sketch=f.GetSpecificFeature2
   for a in ['GetSketchSegments','GetSketchPoints2','GetRelations','RelationManager','GetReferenceEntity','GetSketchStatus']:
    try:print(a,getattr(sketch,a),flush=True)
    except Exception:pass
 f=f.GetNextFeature
