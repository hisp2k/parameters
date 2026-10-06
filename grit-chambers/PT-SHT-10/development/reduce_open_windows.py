from pathlib import Path
import pythoncom,win32com.client as w,json
s=w.Dispatch('SldWorks.Application');active=s.ActiveDoc;active_path=active.GetPathName
root=(Path.cwd()/'work').resolve();recovery=root/'recovered-open-parts';recovery.mkdir(exist_ok=True)
docs=list(s.GetDocuments);log=[]
for d in docs:
 path=d.GetPathName;title=d.GetTitle
 if path==active_path:continue
 if path:
  resolved=Path(path).resolve()
  if not resolved.is_relative_to(root):continue
  if d.GetSaveFlag:
   e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
   ok=d.Save3(1,e,v);log.append({'title':title,'saved':ok,'error':e.value,'warning':v.value})
   if not ok:print('save fail',title,e.value,flush=True);continue
 elif title in ['Деталь1','Деталь12']:
  if d.GetSaveFlag:
   dest=recovery/(title+'.SLDPRT');r=d.SaveAs3(str(dest),0,0);log.append({'title':title,'recovered':str(dest),'result':r})
   if not dest.exists():continue
 else:continue
 s.CloseDoc(title);print('closed',title,flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('main save',active.Save3(1,e,v),e.value,v.value,flush=True)
(root/'open_window_recovery_log.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
