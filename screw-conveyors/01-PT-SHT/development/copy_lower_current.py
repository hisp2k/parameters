from pathlib import Path
import json
import pythoncom
import win32com.client as w
sw=w.GetActiveObject('SldWorks.Application')
d=next(x for x in sw.GetDocuments if x.GetTitle=="PT.SHT.01.23.00.00 СБ 'Обойма нижняя' — восстановлено.SLDASM")
out=Path('work/lower_interference_trial').resolve();out.mkdir(exist_ok=True)
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
sw.ActivateDoc3(d.GetTitle,False,2,err)
d.ClearSelection2(True)
warning=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
target=out/'Обойма нижняя — контроль интерференций.SLDASM'
empty=w.VARIANT(pythoncom.VT_DISPATCH,None)
ok=d.Extension.SaveAs2(str(target),0,7,empty,'_NI_20261004',False,err,warning)
print('saved_copy',ok,err.value,warning.value,'original',d.GetPathName,'dirty',bool(d.GetSaveFlag),flush=True)
if not ok or err.value:raise RuntimeError('Copy failed')
spec=sw.GetOpenDocSpec(str(target));spec.DocumentType=2;spec.Silent=True
trial=sw.OpenDoc7(spec)
if trial is None:raise RuntimeError('Copy did not open')
rows=[{'name':c.Name2,'path':c.GetPathName} for c in trial.GetComponents(False)]
(out/'references.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('components',len(rows),'external',len([r for r in rows if not r['path'].startswith(str(out))]),flush=True)
