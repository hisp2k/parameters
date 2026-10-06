from pathlib import Path
import pythoncom
import win32com.client as w
pythoncom.CoInitialize()
s=w.DispatchEx('SldWorks.Application')
try:
    print('load',s.LoadAddIn(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll'),flush=True)
    m=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
    e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    q=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    d=s.OpenDoc6(str(m),2,64,'',e,q)
    print('open',bool(d),e.value,q.value,flush=True)
    a=s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')
    x=a.GetNGPInterface()
    print('ngp',bool(x),x._oleobj_.GetTypeInfo().GetDocumentation(-1)[0] if x else None,flush=True)
    y=a.GetAPI().IActiveDoc
    print('projects',y.Projects,flush=True)
finally:
    try:s.ExitApp()
    except Exception as exc:print('exit',repr(exc),flush=True)
