from pathlib import Path
import json,math
from PIL import Image
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/joint_r07.json').read_text(encoding='utf8'));r=json.loads((B/'work/joint_prototype_report_r07.json').read_text(encoding='utf8'));assert r['ok']
def canonical(n):
 if n.startswith('RAIL_HOLE_'):
  side,direction=n.replace('RAIL_HOLE_','').split('_');return f'REF_RAIL_{side}_{direction}_SLOPE'
 return n
def check(bs):
 assert len(bs)==69;assert set(canonical(x['name']) for x in bs)==set(d['expected_bodies'])
 errors=[]
 for x in bs:
  e=d['expected_bodies'][canonical(x['name'])];v=abs(x['volume_m3']-e['volume_m3']);c=max(abs(y-z/1000) for y,z in zip(x['centroid_m'],e['centroid_mm']));assert v<1e-10,(x['name'],v);assert c<1e-9,(x['name'],c);errors.append((v,c))
 return dict(bodies=69,max_volume_difference_m3=max(x[0] for x in errors),max_centroid_difference_m=max(x[1] for x in errors),all_individual_volumes_centroids_match=True)
qa=[check(r['variants'][0]['bodies']),check(r['reopened_bodies'])];sets=[r['variants'][0]['intersections'],r['reopened_intersections'],r['stroke_minus6_intersections'],r['stroke_plus6_intersections']]
for xs in sets:assert len(xs)==2346 and all(x['volume_m3']<1e-10 and x['api_code'] in [0,5,6,1067] for x in xs)
assert r['previous_before']==r['previous_after'];assert r['save_errors']==0 and r['save_warnings']==0
r['prior_document_unchanged']=True;r.pop('previous_before');r.pop('previous_after');r['independent_verification']=qa;r['all_intersection_operations']=9384;r['stroke_check_method']='Temporary copied bodies translated dx=±6 mm, dy=−dx*tan(1.5°); original CAD unchanged. Both OUT rail ends and their 6 fastener bodies translated.';r['model_angle_deg']=1.5;r['stroke_not_temperature_or_dynamic_validation']=True;r['preview_visually_checked']=False
(O/'11_Испытания_и_контроль/Проверка_CAD_крепления_и_стыка_R07.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
Image.open(B/'work/joint_native_r07.bmp').save(O/'03_Модели_SolidWorks/ЛТ500_Крепление_и_стык_вид_R07.png')
print(json.dumps({'verification':qa,'boolean_operations':9384,'stroke_geometry':'passed','save':'passed'}))
