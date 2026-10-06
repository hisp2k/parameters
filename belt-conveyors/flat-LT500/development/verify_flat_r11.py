from pathlib import Path
import json
from PIL import Image
B=Path(r'C:\Users\adm\Documents\Codex\2026-10-04\new-chat-2');O=B/'outputs/Ленточный_транспортер';d=json.loads((B/'work/flat_roller_r11.json').read_text(encoding='utf8'));r=json.loads((B/'work/flat_native_report_r11.json').read_text(encoding='utf8'));assert r['ok'],r.get('error')
aliases={'SHAFT_FLAT_4':'SHAFT','HOLE_STATOR_LEFT':'STATOR_LEFT','HOLE_STATOR_RIGHT':'STATOR_RIGHT'}
def name(x):
 n=x['name'].removesuffix('_SLOPE');return aliases.get(n,n)
def check(bs):
 assert len(bs)==34 and set(name(x) for x in bs)==set(d['expected_bodies'])
 errs=[]
 for x in bs:
  e=d['expected_bodies'][name(x)];v=abs(x['volume_m3']-e['volume_m3']);c=max(abs(y-z) for y,z in zip(x['centroid_m'],e['centroid_m']));assert v<1e-10,(x['name'],v);assert c<1e-7,(x['name'],c);errs.append((v,c))
 return dict(max_volume_difference_m3=max(x[0] for x in errs),max_centroid_difference_m=max(x[1] for x in errs),individual_bodies_verified=34)
checks=[check(r['bodies_before_save']),check(r['reopened_bodies'])]
for k in ['intersections_before_save','reopened_intersections']:assert len(r[k])==561 and all(x['volume_m3']<1e-10 for x in r[k])
assert len(r['service_intersections'])==153 and all(x['volume_m3']<1e-10 for x in r['service_intersections'])
assert r['isolated_instance'] and r['save_errors']==0 and r['save_warnings']==0
r.update(independent_geometry_verification=checks,CAD_feature_name_to_calculation_part_aliases=aliases,centroid_comparison_tolerance_m=1e-7,centroid_comparison_note='0.0001mm is a geometric comparison tolerance, not a manufacturing tolerance; cylinder/annulus intersection differs slightly from independent quadrature',volume_comparison_tolerance_m3=1e-10,assembly_intersection_operations=1122,service_position_intersection_operations=153,service_position='M6 removed; keepers translated15mm outward; roller/shaft/stators raised35mm normal to frame; no belt modeled',continuous_service_path_checked=False,simulation_performed=False,actual_threads_or_bearing_ring_contacts_verified=False,preview_visually_checked=False)
(O/'11_Испытания_и_контроль/Проверка_CAD_плоского_ролика_R11.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf8')
Image.open(B/'work/flat_native_r11.bmp').save(O/'03_Модели_SolidWorks/ЛТ500_Плоский_ролик_вид_R11.png')
print(json.dumps(dict(independent_geometry=checks,intersections=1275)))
