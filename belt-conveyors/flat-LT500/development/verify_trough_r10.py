from pathlib import Path
import json
from PIL import Image
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/trough_r10.json').read_text(encoding='utf8'));r=json.loads((B/'work/trough_prototype_report_r10.json').read_text(encoding='utf8'));assert r['ok'],r.get('error')
def canonical(n):return n.removesuffix('_SLOPE').removesuffix('_WING')
def check(bs):
 assert len(bs)==34
 assert set(canonical(x['name']) for x in bs)==set(d['expected_bodies'])
 errors=[]
 for x in bs:
  e=d['expected_bodies'][canonical(x['name'])];v=abs(x['volume_m3']-e['volume_m3']);c=max(abs(y-z) for y,z in zip(x['centroid_m'],e['centroid_m']));assert v<1e-10,(x['name'],v);assert c<1e-9,(x['name'],c);errors.append((v,c))
 return dict(bodies=34,max_volume_difference_m3=max(x[0] for x in errors),max_centroid_difference_m=max(x[1] for x in errors),all_individual_volumes_centroids_match=True)
qa=[check(r['bodies_before_save']),check(r['reopened_bodies'])]
for k in ['intersections_before_save','reopened_intersections']:assert len(r[k])==561 and all(x['volume_m3']<1e-10 for x in r[k])
assert r['isolated_instance'] and r['save_errors']==0 and r['save_warnings']==0
r.update(CAD_built_in_separate_owned_process=True,independent_verification=qa,all_intersection_operations=1122,preview_visually_checked=False,assembly_mates_or_motion_tested=False,simulation_performed=False,body_count=34)
(O/'11_Испытания_и_контроль/Проверка_CAD_желобчатого_узла_R10.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
Image.open(B/'work/trough_native_r10.bmp').save(O/'03_Модели_SolidWorks/ЛТ500_Желобчатый_узел_вид_R10.png')
print(json.dumps(dict(verification=qa,intersection_operations=1122)))
