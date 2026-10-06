from pathlib import Path
import json
import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
lib = pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
types = {lib.GetDocumentation(i)[0]: lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount())}
def typed(obj, name):
    return win32.dynamic.Dispatch(obj._oleobj_ if hasattr(obj, '_oleobj_') else obj, typeinfo=types[name])
sw = win32.Dispatch('SldWorks.Application')
st = typed(sw, 'ISldWorks')
base = Path.cwd() / 'work' / 'pt-sht-10-210l'
path = next((base / 'Модель').glob('*Бункер в сборе.SLDASM'))
result, error = st.ActivateDoc3(str(path), False, 0, 0)
print('ACTIVATE', result, error, st.ActiveDoc.GetPathName, flush=True)
assert result and 'pt-sht-10-210l' in st.ActiveDoc.GetPathName
a = typed(result, 'IAssemblyDoc')
mu = typed(st.GetMathUtility(), 'IMathUtility')
identity = mu.CreateTransform(win32.VARIANT(pythoncom.VT_ARRAY | pythoncom.VT_R8,
    (1.,0.,0., 0.,1.,0., 0.,0.,1., 0.,0.,0., 1.,0.,0.,0.)))
already = {c.Name2.split('-')[0] for c in a.GetComponents(False) or []}
rows = []
for p in sorted((base / 'CADparts').glob('CAD210_*.SLDPRT')):
    if p.stem in already:
        continue
    open_error = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    open_warn = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    part = sw.GetOpenDocumentByName(str(p)) or sw.OpenDoc6(str(p), 1, 3, '', open_error, open_warn)
    assert part, (p, open_error.value)
    result, error = st.ActivateDoc3(str(path), False, 0, 0)
    assert result and error == 0
    raw = a.AddComponent4(str(p), '', 0., 0., 0.)
    print('RAW', p.name, raw, flush=True)
    assert raw, p
    c = typed(raw, 'IComponent2')
    print('ACTIVE', st.ActiveDoc.GetPathName, flush=True)
    assert c.SetTransformAndSolve2(identity), p
    a.ClearSelection2(True)
    assert c.Select4(False, None, False)
    a.FixComponent
    rows.append({'name': c.Name2, 'file': str(p), 'box': list(c.GetBox(False, False))})
    print('ADD', rows[-1], flush=True)
print('REBUILD', a.ForceRebuild3(False), flush=True)
se = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
swr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
print('SAVE', a.Save3(1, se, swr), se.value, swr.value, flush=True)
Path('work/build_210l_log.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
