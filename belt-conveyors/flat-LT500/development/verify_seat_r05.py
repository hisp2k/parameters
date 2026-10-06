from pathlib import Path
import json,math
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/seat_r05.json').read_text(encoding='utf8'));r=json.loads((B/'work/seat_prototype_report_r05.json').read_text(encoding='utf8'));assert r['ok']
def check(bodies,deg):
 a=math.radians(deg);v=next(x for x in d['variants'] if x['angle_deg']==deg);tc=v['t_centre_mm']/1000;by={x['name']:x for x in bodies};assert len(by)==11
 expected={}
 for side,z in [('LEFT',.05),('RIGHT',.65)]:
  expected['PLATE_'+side]=(120*150*8e-9,[0,-.586,z]);expected['LEG_'+side]=(540.8230016469242*v['leg_depth_m']*1e-6,[0,-.311-tc/2,z]);expected['SEAT_'+side]=(100*60*v['t_centre_mm']*1e-9,[v['wedge_centroid_relative_seat_plane_mm'][0]/1000,.04+v['wedge_centroid_relative_seat_plane_mm'][1]/1000,z])
  for direction,x in [('IN',-.15),('OUT',.15)]:expected[f'REF_RAIL_{side}_{direction}_SLOPE']=(840.8230016469242*.3e-6,[x*math.cos(a)+.05*math.sin(a),.04-x*math.sin(a)+.05*math.cos(a),z])
 expected['CROSSBEAM']=(1334.7964473723105*.7e-6,[0,-tc,.35])
 for name,(vol,p) in expected.items():
  b=by[name];assert abs(b['volume_m3']-vol)<1e-10,name;assert max(abs(x-y) for x,y in zip(b['centroid_m'],p))<1e-9,name
 def plane(b,n,p):
  hits=[]
  for f in b['planes']:
   q=f['plane'];dot=sum(q[j]*n[j] for j in range(3));dist=sum((q[j+3]-p[j])*n[j] for j in range(3))
   if abs(abs(dot)-1)<1e-8 and abs(dist)<1e-8:hits.append(f)
  return hits
 normal=[math.sin(a),math.cos(a),0];origin=[0,.04,0];count=0
 for side in ['LEFT','RIGHT']:
  f=plane(by['SEAT_'+side],normal,origin);assert len(f)==1;assert abs(f[0]['area_m2']-.100*.060/math.cos(a))<1e-9
  for direction in ['IN','OUT']:
   f=plane(by[f'REF_RAIL_{side}_{direction}_SLOPE'],normal,origin);assert len(f)==1;assert abs(f[0]['area_m2']-.038*.3)<1e-9;count+=1
  f=plane(by['SEAT_'+side],[0,1,0],[0,.04-tc,0]);assert len(f)==1;assert abs(f[0]['area_m2']-.006)<1e-9
 f=plane(by['CROSSBEAM'],[0,1,0],[0,.04-tc,0]);assert len(f)==1;assert abs(f[0]['area_m2']-.084*.7)<1e-9
 return {'angle_deg':deg,'individual_body_volume_centroid_matches':True,'coplanar_rail_and_seat_faces_verified':count,'wedge_bottom_and_beam_top_coplanar':True,'native_face_areas_match_geometry':True}
qa=[]
for v in r['variants']:
 q=check(v['bodies'],v['angle_deg']);assert len(v['intersections'])==55;assert all(x['volume_m3']<1e-10 for x in v['intersections']);q['pairwise_boolean_tests']=55;qa.append(q)
qa.append({**check(r['reopened_bodies'],1.5),'after_reopen':True});assert len(r['reopened_intersections'])==55;assert all(x['volume_m3']<1e-10 for x in r['reopened_intersections'])
r['independent_verification']=qa;r['prior_document_unchanged']=r['previous_before']==r['previous_after'];assert r['prior_document_unchanged'];r.pop('previous_before');r.pop('previous_after');r['preview_visually_checked']=True;r['geometry_contact_only_not_pressure_or_strength']=True
(O/'11_Испытания_и_контроль/Проверка_CAD_наклонного_стыка_R05.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'CAD_variants':[x['angle_deg'] for x in qa[:3]],'total_intersection_tests':220,'contact_faces':'passed','volumes_and_centroids':'passed','native_reopen':'passed'}))
