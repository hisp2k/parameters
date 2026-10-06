import json
from pathlib import Path
from collections import defaultdict
base=Path('outputs/Шнек 1 — параметрическая модель')
r=json.loads((base/'full_interference_audit_20261004_before.json').read_text(encoding='utf-8'))
g=defaultdict(lambda:[0,0.])
for a in r['interferences']:
 if a['volume_mm3']<.001:continue
 key=tuple(sorted(a['components']));g[key][0]+=1;g[key][1]+=a['volume_mm3']
print('significant pairs',len(g))
for key,(count,vol) in sorted(g.items(),key=lambda x:-x[1][1]):
 if key[0]==key[1]:continue
 print(count,round(vol,3),' | '.join(key))
print('MATES')
for a in json.loads((base/'mate_diagnostics_20261004.json').read_text(encoding='utf-8')):
 for e in a['errors']:
  if e['type'].startswith('Mate'):print(e['name'],e['type'],[(x.get('component'),x.get('reference_present'),x.get('params')) for x in e.get('entities',[])])
