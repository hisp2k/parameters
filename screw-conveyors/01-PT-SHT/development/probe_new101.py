exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
for m in mates(doc):
 if m.GetTypeName2=='MateCoincident' and (m.Name=='Совпадение101' or m.Name not in [e['name'] for a in json.loads((base/'mate_diagnostics_20261004.json').read_text(encoding='utf-8')) for e in a['errors']]):
  es=[m.GetSpecificFeature2.MateEntity(i).ReferenceComponent.Name2 for i in (0,1)]
  if any('М8х25 DIN 933-9' in n for n in es):print(m.Name,m.GetErrorCode,m.IsSuppressed,es)
