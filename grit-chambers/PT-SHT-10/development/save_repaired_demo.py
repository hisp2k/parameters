from pathlib import Path
import pythoncom,win32com.client as w,json
s=w.Dispatch('SldWorks.Application');root=(Path.cwd()/'work'/'pt-sht-10-demo').resolve();log=[]
for d in list(s.GetDocuments):
 path=d.GetPathName
 if not path or not Path(path).resolve().is_relative_to(root):continue
 if not d.GetSaveFlag:continue
 e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
 ok=d.Save3(1,e,v);row={'path':path,'saved':ok,'error':e.value,'warning':v.value};log.append(row);print(row,flush=True)
 if not ok:raise RuntimeError('Save failed')
Path('work/repaired_demo_save_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
