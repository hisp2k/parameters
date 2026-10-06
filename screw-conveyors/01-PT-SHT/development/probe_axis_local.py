exec(open('work/general_mate_geometry.py',encoding='utf-8-sig').read().split('for m in mates(doc):')[0])
support=next(c.GetModelDoc2 for c in doc.GetComponents(True) if 'Опора шнековая' in c.Name2)
r=json.loads((base/'mate_diagnostics_20261004.json').read_text(encoding='utf-8'));src=next(a for a in r if 'Опора шнековая' in a['assembly'])
for e in src['errors']:
 if e['name'] not in ['Расстояние5','Расстояние6','Расстояние8','Расстояние9']:continue
 print(e['name'])
 for ent in e['entities']:
  if ent['reference_present']:continue
  c=next(c for c in support.GetComponents(True) if c.Name2==ent['component']);p=ent['params'];t=list(c.Transform2.ArrayData)
  point=[sum((p[i]-t[9+i])*t[j*3+i] for i in range(3)) for j in range(3)];v=[sum(p[3+i]*t[j*3+i] for i in range(3)) for j in range(3)]
  print('point',point,'dir',v,flush=True)
