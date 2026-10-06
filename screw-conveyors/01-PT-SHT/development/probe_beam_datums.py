exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
c=next(c for c in support.GetComponents(True) if c.Name2.startswith('PT.SHT.01.25.00.07 ') and c.Name2.endswith('-1'))
f=c.GetModelDoc2.FirstFeature
while f:
 if f.GetTypeName2 in ['RefPlane','RefAxis']:
  print(f.Name,f.GetTypeName2)
  try:print('mt',list(f.GetSpecificFeature2.Transform.ArrayData))
  except Exception:pass
  try:print('axis',f.GetSpecificFeature2.GetRefAxisParams)
  except Exception:pass
 f=f.GetNextFeature
print('transform',list(c.Transform2.ArrayData))
