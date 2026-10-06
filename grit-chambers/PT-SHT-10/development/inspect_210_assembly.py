from pathlib import Path
import json
import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
lib = pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
types = {lib.GetDocumentation(i)[0]: lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount())}
def typed(obj, name):
    return win32.dynamic.Dispatch(obj._oleobj_ if hasattr(obj, '_oleobj_') else obj, typeinfo=types[name])
def value(obj):
    return obj() if callable(obj) else obj
sw = win32.Dispatch('SldWorks.Application')
base = Path.cwd() / 'work' / 'pt-sht-10-210l' / 'Модель'
path = next(base.glob('*Бункер в сборе.SLDASM'))
er = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
wr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
a = typed(sw.OpenDoc6(str(path), 2, 3, '', er, wr), 'IAssemblyDoc')
print('opened', a.GetPathName, er.value, wr.value, flush=True)
rows = []
for raw in a.GetComponents(False) or []:
    c = typed(raw, 'IComponent2')
    try:
        box = list(c.GetBox(False, False))
    except Exception:
        box = None
    try:
        body = c.GetBody()
        has_body = bool(body)
    except Exception:
        has_body = False
    rows.append({'name': c.Name2, 'path': value(c.GetPathName), 'suppression': value(c.GetSuppression), 'box': box, 'body': has_body})
Path('work/inspect_210_assembly.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
for row in rows:
    if row['body'] or 'CFD_' in row['name']:
        print(row, flush=True)
