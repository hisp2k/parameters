from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application');base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель';p=next(base.glob('*Бункер в сборе.SLDASM'))
d=s.GetOpenDocumentByName(str(p));print('doc',d.GetPathName,flush=True)
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',d.Save3(1,e,v),e.value,v.value,flush=True)
print('close',s.CloseDoc(d.GetTitle),flush=True)
d=s.OpenDoc6(str(p),2,64,'',e,v)
print('reopen',bool(d),e.value,v.value,d.GetPathName if d else None,flush=True)
