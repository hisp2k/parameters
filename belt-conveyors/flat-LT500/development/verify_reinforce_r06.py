from pathlib import Path
import json, math
from PIL import Image
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2'); O=B/'outputs/Ленточный_транспортер'
d=json.loads((B/'work/reinforce_r06.json').read_text(encoding='utf8')); old=json.loads((B/'work/seat_r05.json').read_text(encoding='utf8')); r=json.loads((B/'work/reinforce_prototype_report_r06.json').read_text(encoding='utf8')); assert r['ok']
Image.open(B/'work/reinforce_native_r06.bmp').save(O/'03_Модели_SolidWorks/ЛТ500_Усиление_опоры_вид_R06.png')
def check(bodies,deg):
 a=math.radians(deg); v=next(x for x in d['variants'] if x['angle_deg']==deg); ov=next(x for x in old['variants'] if x['angle_deg']==deg);tc=v['t_centre_seat_mm']/1000;by={x['name']:x for x in bodies}; assert len(by)==17
 expected={'CROSSBEAM':(1334.7964473723105*.7e-6,[0,-tc-.012,.35])}
 for side,z in [('LEFT',.05),('RIGHT',.65)]:
  expected['PLATE_'+side]=(120*150*8e-9,[0,-.586,z]);expected['LEG_'+side]=(540.8230016469242*v['leg_depth_m']*1e-6,[0,-.311-tc/2-.006,z]);expected['SEAT_'+side]=(100*60*v['t_centre_seat_mm']*1e-9,[ov['wedge_centroid_relative_seat_plane_mm'][0]/1000,.04+ov['wedge_centroid_relative_seat_plane_mm'][1]/1000,z]);expected['CAP_'+side]=(120*80*12e-9,[0,.04-tc-.006,z])
  for label,x in [('MINUS',-.053),('PLUS',.053)]:expected[f'WEB_{side}_{label}']=(6*80*80e-9,[x,-tc-.012,z])
  for direction,x in [('IN',-.15),('OUT',.15)]:expected[f'REF_RAIL_{side}_{direction}_SLOPE']=(840.8230016469242*.3e-6,[x*math.cos(a)+.05*math.sin(a),.04-x*math.sin(a)+.05*math.cos(a),z])
 for name,(vol,p) in expected.items():
  b=by[name];assert abs(b['volume_m3']-vol)<1e-10,name;assert max(abs(x-y) for x,y in zip(b['centroid_m'],p))<1e-9,name
 assert abs(sum(b['volume_m3'] for b in bodies)-v['with_reference_rails_volume_m3'])<1e-10
 def plane(name,n,p,area):
  hits=[]
  for f in by[name]['planes']:
   q=f['plane'];dot=sum(q[j]*n[j] for j in range(3));dist=sum((q[j+3]-p[j])*n[j] for j in range(3))
   if abs(abs(dot)-1)<1e-8 and abs(dist)<1e-8:hits.append(f)
  assert len(hits)==1,(name,hits);assert abs(hits[0]['area_m2']-area)<1e-9,name
 for side,z in [('LEFT',.05),('RIGHT',.65)]:
  plane('SEAT_'+side,[math.sin(a),math.cos(a),0],[0,.04,0],.100*.060/math.cos(a))
  for direction in ['IN','OUT']:plane(f'REF_RAIL_{side}_{direction}_SLOPE',[math.sin(a),math.cos(a),0],[0,.04,0],.038*.3)
  plane('SEAT_'+side,[0,1,0],[0,.04-tc,0],.006)
  plane('CAP_'+side,[0,1,0],[0,.04-tc,0],.0096)
  plane('CAP_'+side,[0,1,0],[0,.04-tc-.012,0],.0096)
  for label,x in [('MINUS',-.050),('PLUS',.050)]:
   plane(f'WEB_{side}_{label}',[0,1,0],[0,.04-tc-.012,0],.00048)
   plane(f'WEB_{side}_{label}',[1,0,0],[x,0,0],.0064)
 plane('CROSSBEAM',[0,1,0],[0,.04-tc-.012,0],.084*.7)
 for x in [-.05,.05]:plane('CROSSBEAM',[1,0,0],[x,0,0],.064*.7)
 return dict(angle_deg=deg,individual_body_volume_centroid_matches=True,rail_seat_cap_web_planes_and_areas_verified=True,web_inner_faces_match_tube_sides=True,finite_web_contact_height_mm=64,contact_is_geometric_not_strength=True)
qa=[]
for v in r['variants']:
 q=check(v['bodies'],v['angle_deg']);assert len(v['intersections'])==136;assert all(x['volume_m3']<1e-10 and x['api_code'] in [0,5,6,1067] for x in v['intersections']);q['pairwise_boolean_tests']=136;qa.append(q)
qa.append({**check(r['reopened_bodies'],1.5),'after_reopen':True});assert len(r['reopened_intersections'])==136;assert all(x['volume_m3']<1e-10 and x['api_code'] in [0,5,6,1067] for x in r['reopened_intersections'])
r['independent_verification']=qa;r['prior_document_unchanged']=r['previous_before']==r['previous_after'];assert r['prior_document_unchanged'];r.pop('previous_before');r.pop('previous_after');r['preview_visually_checked']=False;r['geometry_contact_only_not_pressure_or_strength']=True
(O/'11_Испытания_и_контроль/Проверка_CAD_усиления_R06.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'CAD_variants':[x['angle_deg'] for x in qa[:3]],'total_intersection_tests':544,'contact_planes':'passed','volumes_and_centroids':'passed','native_reopen':'passed','save_details':{k:v for k,v in r.items() if ('error' in k or 'warn' in k or 'rebuild' in k)}}))
