import pythoncom,win32com.client as w
from pathlib import Path
s=w.Dispatch('SldWorks.Application')
p=Path.cwd()/'work'/'flow-api-reference'/'ball valve.sldasm'
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);v=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
d=s.OpenDoc6(str(p),2,64,'',e,v)
print('open',bool(d),'err',e.value,'warn',v.value,'path',d.GetPathName if d else None,flush=True)
