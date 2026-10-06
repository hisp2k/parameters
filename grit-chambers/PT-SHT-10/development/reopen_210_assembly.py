from pathlib import Path
import json,pythoncom,win32com.client as win32
pythoncom.CoInitialize()
sw=win32.Dispatch('SldWorks.Application')
path=str((Path.cwd()/'work'/'pt-sht-10-210l'/'Модель'/'PT-SHT-10-210L.SLDASM').resolve())
doc=sw.GetOpenDocumentByName(path)
assert doc
er=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
wr=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('SAVE',doc.Save3(1,er,wr),er.value,wr.value,flush=True)
sw.CloseDoc(doc.GetTitle)
doc=sw.OpenDoc6(path,2,1,'',er,wr)
assert doc and doc.GetPathName.lower()==path.lower(),(er.value,wr.value)
rows=[]
for c in doc.GetComponents(False) or []:
    if 'CAD210_' in c.Name2:
        rows.append({'name':c.Name2,'suppression':c.GetSuppression,'path':c.GetPathName})
print('PARTS',len(rows),flush=True)
for r in rows:print(r,flush=True)
assert len(rows)>=16
assert all(r['suppression']!=0 for r in rows)
assert all(Path(r['path']).exists() for r in rows)
Path('work/reopen_210_assembly.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
