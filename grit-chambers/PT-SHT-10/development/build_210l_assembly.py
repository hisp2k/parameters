"""Create a separate hydraulic CAD revision by inserting 175 mm at CAD y=600 mm."""
from pathlib import Path
import json
import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
lib = pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
types = {lib.GetDocumentation(i)[0]: lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount())}
def typed(obj, name):
    return win32.dynamic.Dispatch(obj._oleobj_ if hasattr(obj, '_oleobj_') else obj, typeinfo=types[name])
def arr(values):
    return win32.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8, tuple(values))
def call(value):
    return value() if callable(value) else value

sw = win32.Dispatch('SldWorks.Application')
sw_typed = typed(sw, 'ISldWorks')
modeler = typed(sw_typed.GetModeler(), 'IModeler')
math = typed(sw_typed.GetMathUtility(), 'IMathUtility')
base = Path.cwd() / 'work' / 'pt-sht-10-210l' / 'Модель'
generated_dir = base.parent / 'CADparts'
generated_dir.mkdir(exist_ok=True)
asm_path = next(base.glob('*Бункер в сборе.SLDASM'))
er = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
wr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
asm = typed(sw.OpenDoc6(str(asm_path), 2, 3, '', er, wr), 'IAssemblyDoc')
assert asm and 'pt-sht-10-210l' in asm.GetPathName
print('ASSEMBLY', asm.GetPathName, flush=True)

def cuboid(x0, y0, z0, x1, y1, z1):
    return typed(modeler.CreateBodyFromBox(arr(((x0+x1)/2, (y0+y1)/2, z0,
                                                0., 0., 1., x1-x0, y1-y0, z1-z0))), 'IBody2')
def cyl(radius, y, height):
    return typed(modeler.CreateBodyFromCyl(arr((0., y, 0., 0., 1., 0., radius, height))), 'IBody2')
def op(a, b, code):
    aa = typed(a.Copy(), 'IBody2')
    bb = typed(b.Copy(), 'IBody2')
    result, err = aa.Operations2(code, bb, 0)
    if not result or err:
        raise RuntimeError(f'boolean {code}: {err}')
    return [typed(x, 'IBody2') for x in result]
def shifted(body):
    result = typed(body.Copy(), 'IBody2')
    tr = math.CreateTransform(arr((1.,0.,0., 0.,1.,0., 0.,0.,1., 0.,.175,0., 1.,0.,0.,0.)))
    assert result.ApplyTransform(tr)
    return result
def world_body(component):
    b = typed(component.GetBody(), 'IBody2')
    copy = typed(b.Copy(), 'IBody2')
    assert copy.ApplyTransform(component.Transform2)
    return copy
def save_part(body, stem):
    part = sw.NewDocument(r'C:\ProgramData\SOLIDWORKS\SOLIDWORKS 2026\templates\gost-part.prtdot', 0, 0, 0)
    assert part
    feature = typed(part, 'IPartDoc').CreateFeatureFromBody3(body, False, 0)
    assert feature, stem
    target = generated_dir / (stem + '.SLDPRT')
    saved = part.SaveAs3(str(target), 0, 0)
    print('SAVE PART', stem, saved, flush=True)
    assert target.exists() and target.stat().st_size > 1000, stem
    print('PART', stem, list(body.GetBodyBox()), target.stat().st_size, flush=True)
    sw.CloseDoc(call(part.GetTitle))
    return target

parts = []
retire = []
rows = []
keys = {'CFD_cylinder_welded': ('outer', .3001, .2969),
        'Цилиндр внутренний': ('inner', .2, .197),
        'Труба внутренняя': ('return', .038, .035)}
for raw in asm.GetComponents(False) or []:
    c = typed(raw, 'IComponent2')
    if call(c.GetSuppression) != 2:
        continue
    body = c.GetBody()
    if not body:
        continue
    name = c.Name2
    leaf = name.split('/')[-1]
    original = world_body(c)
    bounds = list(original.GetBodyBox())
    match = next((spec for key, spec in keys.items() if key in leaf), None)
    if match:
        label, r_outer, r_inner = match
        lower = op(original, cuboid(-1., -1., -1., 1., .6, 1.), 15901)[0]
        upper = shifted(op(original, cuboid(-1., .6, -1., 1., 2., 1.), 15901)[0])
        link = op(cyl(r_outer, .5999, .1752), cyl(r_inner, .5999, .1752), 15902)[0]
        for suffix, b in [('lower', lower), ('insert175', link), ('upper', upper)]:
            parts.append(save_part(b, f'CAD210_{label}_{suffix}'))
        retire.append(c)
        rows.append({'old': name, 'action': 'split_insert_175', 'old_box': bounds})
    elif bounds[1] > .6 and bounds[4] > .6:
        # The upper cover, seals, inlet nozzle, flange and inlet lid move together.
        new = shifted(original)
        label = f'CAD210_shift_{len(parts):02d}'
        parts.append(save_part(new, label))
        retire.append(c)
        rows.append({'old': name, 'action': 'shift_175', 'old_box': bounds})

assert len([r for r in rows if r['action']=='split_insert_175']) == 3, rows
assert len([r for r in rows if r['action']=='shift_175']) >= 5, rows
print('RETIRE', len(retire), 'PARTS', len(parts), flush=True)
sw.ActivateDoc3(asm.GetTitle, False, 0, 0)
asm.ClearSelection2(True)
for c in retire:
    assert c.Select4(True, None, False), c.Name2
print('SUPPRESS', asm.EditSuppress2, flush=True)
asm.ClearSelection2(True)
identity = math.CreateTransform(arr((1.,0.,0., 0.,1.,0., 0.,0.,1., 0.,0.,0., 1.,0.,0.,0.)))
for path in parts:
    comp = typed(asm.AddComponent4(str(path), '', 0., 0., 0.), 'IComponent2')
    assert comp and comp.SetTransformAndSolve2(identity), str(path)
    asm.ClearSelection2(True)
    assert comp.Select4(False, None, False)
    asm.FixComponent
    rows.append({'new': comp.Name2, 'path': str(path), 'box': list(comp.GetBox(False, False))})
print('REBUILD', asm.ForceRebuild3(False), flush=True)
save_er = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
save_wr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
print('SAVE', asm.Save3(1, save_er, save_wr), save_er.value, save_wr.value, flush=True)
Path('work/build_210l_log.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
