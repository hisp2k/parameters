from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application');base=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель';a=s.GetOpenDocumentByName(str(next(base.glob('*Бункер в сборе.SLDASM'))))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);s.ActivateDoc3(a.GetTitle,False,0,e)
c=a.AddComponent4(str(base/'CFD_top_seal_v2.SLDPRT'),'',0,0.8335,0)
print('insert',bool(c),c.Name2,list(c.GetBox(False,False)) if c else None,flush=True)
print('rebuild',a.ForceRebuild3(False),flush=True)
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warn=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',a.Save3(1,err,warn),err.value,warn.value,flush=True)
