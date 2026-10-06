from pathlib import Path
import json
import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
lib = pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
types = {lib.GetDocumentation(i)[0]: lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount())}
def typed(obj, name):
    return win32.dynamic.Dispatch(obj._oleobj_ if hasattr(obj, '_oleobj_') else obj, typeinfo=types[name])
def call(value):
    return value() if callable(value) else value
sw = win32.Dispatch('SldWorks.Application')
st = typed(sw, 'ISldWorks')
path = Path.cwd() / 'work' / 'pt-sht-10-210l' / 'Модель' / 'PT-SHT-10-210L.SLDASM'
asm = sw.GetOpenDocumentByName(str(path))
if not asm:
    er = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    wr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    asm = sw.OpenDoc6(str(path), 2, 1, '', er, wr)
assert asm and 'pt-sht-10-210l' in call(asm.GetPathName)
asm = typed(asm, 'IAssemblyDoc')
modeler = typed(st.GetModeler(), 'IModeler')
box = typed(modeler.CreateBodyFromBox(win32.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
    (0.,.3,-.5, 0.,0.,1., 1.,1.8,1.))), 'IBody2')
regions = [box]
rows = []
errors = []
for raw in asm.GetComponents(False) or []:
    c = typed(raw, 'IComponent2')
    if call(c.GetSuppression) == 0:
        continue
    leaf = c.Name2.split('/')[-1]
    if not any(x in leaf for x in ['Цилиндр','Конус','Отвод','Труба','Фланец','Крышка глухая','Прокладка','CFD_','CAD210_']):
        continue
    raw_body = c.GetBody()
    if not raw_body:
        continue
    tool = typed(typed(raw_body,'IBody2').Copy(), 'IBody2')
    assert tool.ApplyTransform(c.Transform2), c.Name2
    bounds = list(tool.GetBodyBox())
    faults = typed(tool.Check3, 'IFaultEntity').Count
    if faults:
        errors.append({'component': c.Name2, 'faults': faults})
    next_regions = []
    for region in regions:
        b = list(region.GetBodyBox())
        if any(b[i+3] < bounds[i] or bounds[i+3] < b[i] for i in range(3)):
            next_regions.append(region)
            continue
        aa = typed(region.Copy(), 'IBody2')
        bb = typed(tool.Copy(), 'IBody2')
        result, err = aa.Operations2(15902, bb, 0)
        if not result and err == 547:
            aa = typed(region.Copy(), 'IBody2')
            bb = typed(tool.Copy(), 'IBody2')
            aa.ResetEdgeTolerances()
            bb.ResetEdgeTolerances()
            result, err = aa.Operations2(15902, bb, 0)
        if result:
            next_regions.extend(typed(x, 'IBody2') for x in result)
        elif err in (1067, 5):
            next_regions.append(region)
        elif err != 0:
            next_regions.append(region)
            errors.append({'component': c.Name2, 'boolean_error': err})
    regions = next_regions
    rows.append({'component': c.Name2, 'box': bounds, 'regions_after': len(regions)})
    print('STEP', len(rows), c.Name2, len(regions), flush=True)

results = []
for i, b in enumerate(regions):
    row = {'region': i, 'volume_m3': b.GetMassProperties(1.)[3], 'box': list(b.GetBodyBox()),
           'faults': typed(b.Check3,'IFaultEntity').Count}
    results.append(row)
    print('REGION', row, flush=True)
candidates = [(r,b) for r,b in zip(results,regions) if .18 < r['volume_m3'] < .25]
report = {'assembly': str(path), 'components': rows, 'regions': results, 'errors': errors,
          'cavity_candidates': [r for r,_ in candidates]}
Path('work/verify_210_cavity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(candidates)==1, f'expected one 210 L fluid cavity, got {len(candidates)}'
assert not errors, f'geometry errors: {errors}'
cavity = candidates[0][1]
import math
for label,point in [('inlet',(.2515,.8945,.329)),('main',(0.,.458,.353)),('bottom',(0.,.004,0.))]:
    found=[]
    for raw_face in cavity.GetFaces():
        face=typed(raw_face,'IFace2')
        bounds=face.GetBox()
        if any(point[k]<bounds[k]-1e-8 or point[k]>bounds[k+3]+1e-8 for k in range(3)):
            continue
        nearest=face.GetClosestPointOn(*point)
        if math.dist(point,nearest[:3])<1e-7:
            found.append({'area_m2':face.GetArea(),'box':list(bounds)})
    print('CONTACT',label,found,flush=True)
    report.setdefault('contacts',[]).append({'port':label,'point':point,'faces':found})
Path('work/verify_210_cavity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
part = st.NewPart()
assert part and typed(part,'IPartDoc').CreateFeatureFromBody3(cavity,False,0)
out = Path.cwd() / 'work' / 'pt-sht-10-210l' / 'CADparts' / 'CAD210_fluid_cavity.STL'
ok = part.SaveAs3(str(out), 0, 0)
print('STL',ok,out.stat().st_size if out.exists() else 0,flush=True)
