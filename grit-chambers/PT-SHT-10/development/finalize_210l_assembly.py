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
sw_typed = typed(sw, 'ISldWorks')
mu = typed(sw_typed.GetMathUtility(), 'IMathUtility')
base = Path.cwd() / 'work' / 'pt-sht-10-210l' / 'Модель'
parts = sorted((base.parent / 'CADparts').glob('CAD210_*.SLDPRT'))
assert len(parts) == 16, len(parts)
path = next(base.glob('*Бункер в сборе.SLDASM'))
er = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
wr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
a = typed(sw.OpenDoc6(str(path), 2, 3, '', er, wr), 'IAssemblyDoc')
assert a and 'pt-sht-10-210l' in a.GetPathName
sw_typed.ActivateDoc3(a.GetTitle, False, 0, 0)
names = []
a.ClearSelection2(True)
for raw in a.GetComponents(False) or []:
    c = typed(raw, 'IComponent2')
    if call(c.GetSuppression) != 2:
        continue
    if not c.GetBody():
        continue
    leaf = c.Name2.split('/')[-1]
    box = list(c.GetBox(False, False))
    is_split = any(k in leaf for k in ['CFD_cylinder_welded', 'Цилиндр внутренний', 'Труба внутренняя'])
    is_shift = box[1] > .6 and box[4] > .6
    if not is_split and not is_shift:
        continue
    assert c.Select4(True, None, False), c.Name2
    names.append(c.Name2)
assert len(names) == 10, names
print('SUPPRESS', names, a.EditSuppress2, flush=True)
a.ClearSelection2(True)
identity = mu.CreateTransform(win32.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
    (1.,0.,0., 0.,1.,0., 0.,0.,1., 0.,0.,0., 1.,0.,0.,0.)))
new = []
for p in parts:
    c = typed(a.AddComponent4(str(p), '', 0., 0., 0.), 'IComponent2')
    assert c and c.SetTransformAndSolve2(identity), str(p)
    a.ClearSelection2(True)
    assert c.Select4(False, None, False)
    a.FixComponent
    new.append({'name': c.Name2, 'file': str(p), 'box': list(c.GetBox(False, False))})
    print('ADD', c.Name2, new[-1]['box'], flush=True)
print('REBUILD', a.ForceRebuild3(False), flush=True)
se = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
swr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
print('SAVE', a.Save3(1, se, swr), se.value, swr.value, flush=True)
Path('work/build_210l_log.json').write_text(json.dumps({'retired': names, 'new': new}, ensure_ascii=False, indent=2), encoding='utf-8')
