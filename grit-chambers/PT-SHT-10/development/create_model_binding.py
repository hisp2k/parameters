"""Trace the CFD demonstration back to the source PT-SHT-10 CAD assembly."""
from pathlib import Path
from zipfile import ZipFile
from hashlib import sha256
import json,math,csv,sys

ROOT=Path(r'C:\Users\adm\Desktop\РАБОТА\песколовка\01.PT.SHT (Заказ №2418 - НПСК) предварительный\01.PT.SHT (Заказ №2418 - НПСК)')
SOURCE=ROOT/'Модель'
INVENTORY=ROOT/'КД_проект_20261001'/'Checks'/'source_inventory.json'
DEMO=Path('work/pt-sht-10-demo/Модель')
OUT=Path('outputs')
inventory=json.loads(INVENTORY.read_text(encoding='utf-8'))
def digest(path):
    h=sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

src_items=[];changed=[];unchanged=[];missing=[]
source_names={item['file_name'] for item in inventory['model_files']}
for item in inventory['model_files']:
    src=Path(item['path']);cp=DEMO/item['file_name']
    sh=digest(src) if src.exists() else None
    dh=digest(cp) if cp.exists() else None
    state='missing_demo' if not cp.exists() else ('same_bytes' if sh==dh else 'binary_different_in_demo')
    src_items.append({'file_name':item['file_name'],'source_sha256':sh,'inventory_sha256':item['sha256'],
                      'inventory_still_matches':sh==item['sha256'],'demo_sha256':dh,'comparison':state})
    {'same_bytes':unchanged,'binary_different_in_demo':changed,'missing_demo':missing}[state].append(item['file_name'])
rootname='01.PT.SHT.01.00.00.00 СБ  Бункер в сборе.SLDASM'
src_root=SOURCE/rootname;demo_root=DEMO/rootname
assert src_root.exists() and demo_root.exists()
fld=DEMO/'2'/'2.fld'
assert fld.exists()
archive=OUT/'PT-SHT-10_демо_проект_Flow.zip'
with ZipFile(archive) as z:
    assembly_entries=[n for n in z.namelist() if n.endswith(rootname)]
    fld_entries=[n for n in z.namelist() if n.endswith('/2/2.fld')]
    assert len(assembly_entries)==len(fld_entries)==1
    archived_assembly_sha=sha256(z.read(assembly_entries[0])).hexdigest()
    archived_fld_sha=sha256(z.read(fld_entries[0])).hexdigest()
assert archived_fld_sha==digest(fld)
cavity=json.loads((OUT/'PT-SHT-10_проверка_полости.json').read_text(encoding='utf-8'))
bc=json.loads(Path('work/valid_boundary_conditions.json').read_text(encoding='utf-8'))
ports={c['port']:c for c in cavity['contacts']}
for c in ports.values():assert len(c['touching_faces'])==1 and c['touching_faces'][0]['distance_m']==0
assembly_radius=.297
inlet_offset=ports['inlet']['center_m'][0]
boundary=[]
for row,port,meaning,token in zip(bc,['inlet','main_outlet','bottom_outlet'],['10 m3/h','101325 Pa absolute (about 0 Pa gauge at main outlet)','0.10 m3/h'],['inlet','outlet','bottom']):
    # zip only first three BCs, in the proven order of the checked Flow dump.
    assert token in row['references'][1][0].lower()
    boundary.append({'port':port,'center_m':ports[port]['center_m'],'flow_entity':row['references'][1][0],
                     'flow_entity_uuid':row['references'][0][0],'assigned_condition':meaning,'stored_value_SI':row['value_SI'][1],
                     'face_area_m2':ports[port]['touching_faces'][0]['face_area_m2']})
manifest={
  'product':'Vökker PT-SHT-10 tangential grit separator, order 2418.1',
  'scope':'available source assembly is bunker module 01.PT.SHT.01.00.00.00, not complete product',
  'source_model':{'path':str(src_root),'sha256':digest(src_root),'configuration':None,
                  'revisions_confirmed':False},
  'demo_cfd_model':{'path':str(demo_root),'sha256':digest(demo_root),
                    'configuration':'По умолчанию','flow_project':'PT-SHT-10-demo-Q10-sealed',
                    'flow_file':str(fld.resolve()),'flow_sha256':digest(fld),
                    'working_assembly_saved_after_solver_archive':True},
  'solved_project_snapshot':{'archive_path':str(archive.resolve()),'archive_sha256':digest(archive),
                             'assembly_entry':assembly_entries[0],'assembly_sha256':archived_assembly_sha,
                             'flow_entry':fld_entries[0],'flow_sha256':archived_fld_sha},
  'source_inventory_date':inventory.get('captured_at_utc'),
  'source_files':{'total':len(src_items),'byte_identical_demo':unchanged,'binary_different_demo':changed,'missing_demo':missing,
                  'current_matches_inventory':sum(x['inventory_still_matches'] for x in src_items),'details':src_items},
  'demo_added_cad_files':sorted(p.name for p in DEMO.iterdir() if p.is_file() and p.suffix.upper() in ('.SLDASM','.SLDPRT') and p.name not in source_names),
  'fluid_domain':{'method':cavity['method'],'volume_m3':cavity['volume_m3'],
                  'vertical_axis':'y','gravity_m_s2':[0,-9.81,0],
                  'native_flow_check_geometry_proven':False},
  'boundaries':boundary,
  'inlet_offset_ratio_to_inner_radius':inlet_offset/assembly_radius,
  'model_limitations':['Full 4000x1500x3000 mm product assembly unavailable',
                       'Screw, external pipes, actual discharge backpressure and fill state absent',
                       'Demo seals and lids are not validated production geometry',
                       'Native Check Geometry and particle capture efficiency not confirmed'],
}
OUT.joinpath('PT-SHT-10_привязка_расчёта_к_CAD.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
print('source',manifest['source_model']['sha256'])
print('demo',manifest['demo_cfd_model']['sha256'])
print('flow',manifest['demo_cfd_model']['flow_sha256'])
print('files',len(src_items),'unchanged',len(unchanged),'changed',len(changed),'missing',len(missing),'inventory match',manifest['source_files']['current_matches_inventory'])
print('changed names',changed)
print('missing names',missing)
