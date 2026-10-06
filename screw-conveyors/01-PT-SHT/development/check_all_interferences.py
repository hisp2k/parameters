from pathlib import Path
import json,pythoncom,sys
import win32com.client as w
base=Path('outputs/Шнек 1 — параметрическая модель').resolve();sw=w.GetActiveObject('SldWorks.Application')
path=Path(json.loads((base/'recovered_assembly_check.json').read_text(encoding='utf-8'))['assembly'])
doc=sw.GetOpenDocumentByName(str(path))
if doc is None:
 spec=sw.GetOpenDocSpec(str(path));spec.DocumentType=2;spec.Silent=True;doc=sw.OpenDoc7(spec)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);sw.ActivateDoc3(doc.GetTitle,False,2,e)
print('active',doc.GetTitle,'dirty',doc.GetSaveFlag,flush=True)
mgr=doc.InterferenceDetectionManager
mgr.TreatCoincidenceAsInterference=False;mgr.TreatSubAssembliesAsComponents=False;mgr.IncludeMultibodyPartInterferences=True;mgr.IgnoreHiddenBodies=False;mgr.MakeInterferingPartsTransparent=False;mgr.CreateFastenersFolder=False
try:
 rows=[]
 for item in mgr.GetInterferences or []:
  rows.append({'components':[c.Name2 for c in item.Components or []],'paths':[c.GetPathName for c in item.Components or []],'volume_mm3':float(item.Volume)*1e9})
 data={'assembly':str(path),'count':len(rows),'interferences':rows}
 out=base/('full_interference_audit_20261004_'+(sys.argv[1] if len(sys.argv)>1 else 'before')+'.json');out.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 print('count',len(rows),flush=True)
 for row in rows[:12]:print(round(row['volume_mm3'],3),' | '.join(row['components']),flush=True)
finally:
 if callable(mgr.Done):mgr.Done()

