from pathlib import Path
import json
import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
sw = win32.Dispatch('SldWorks.Application')
lib = pythoncom.LoadTypeLib(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\sldworks.tlb')
types = {lib.GetDocumentation(i)[0]: lib.GetTypeInfo(i) for i in range(lib.GetTypeInfoCount())}
def typed(obj, name):
    return win32.dynamic.Dispatch(obj._oleobj_ if hasattr(obj, '_oleobj_') else obj, typeinfo=types[name])
root = Path.cwd() / 'work' / 'pt-sht-10-210l' / 'Модель'
keys = ['CFD_cylinder_welded', 'Цилиндр внутренний', 'Труба входная', 'CFD_top_cover_sealed', 'CFD_inlet_lid', 'CFD_outlet_lid']
rows = []
for part in root.glob('*.SLDPRT'):
    if not any(k in part.name for k in keys):
        continue
    er = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    wr = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = sw.OpenDoc6(str(part), 1, 3, '', er, wr)
    if not doc:
        rows.append({'file': part.name, 'error': er.value})
        continue
    doc = typed(doc, 'IModelDoc2')
    feats = []
    feat = doc.FirstFeature()
    while feat:
        feat = typed(feat, 'IFeature')
        item = {'name': feat.Name, 'type': feat.GetTypeName2}
        dims = []
        display = feat.GetFirstDisplayDimension()
        while display:
            try:
                dim = display.GetDimension2(0)
                dims.append({'name': dim.FullName, 'value': dim.SystemValue})
            except Exception as exc:
                dims.append({'error': str(exc)})
            display = feat.GetNextDisplayDimension(display)
        if dims:
            item['dimensions'] = dims
        feats.append(item)
        feat = feat.GetNextFeature()
    rows.append({'file': part.name, 'path': doc.GetPathName, 'box': list(doc.GetPartBox(True)), 'features': feats})
Path('work/inspect_210_candidates.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2, default=str), encoding='utf-8')
print(json.dumps(rows, ensure_ascii=False, indent=2, default=str))
