from pathlib import Path
import pythoncom,win32com.client as w
s=w.Dispatch('SldWorks.Application')
p=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
a=s.GetOpenDocumentByName(str(p))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
s.ActivateDoc3(a.GetTitle,False,0,e)
print('active',a.GetPathName,flush=True)
for c in a.GetComponents(False) or []:
 if 'CFD_крышка' in c.Name2:print('present',c.Name2,list(c.GetBox(False,False)),flush=True)
side=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_крышка_боковая.SLDPRT'
bottom=Path.cwd()/'work'/'pt-sht-10-demo'/'Модель'/'CFD_крышка_нижняя.SLDPRT'
c=a.AddComponent4(str(side),'',0.0,0.458,0.3565)
print('outlet',bool(c),c.Name2,list(c.GetBox(False,False)) if c else None,flush=True)
c=a.AddComponent4(str(bottom),'',0.0,0.0005,0.0)
print('bottom',bool(c),c.Name2,list(c.GetBox(False,False)) if c else None,flush=True)
print('rebuild',a.ForceRebuild3(False),flush=True)
err=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0);warn=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
print('save',a.Save3(1,err,warn),'err',err.value,'warn',warn.value,flush=True)
