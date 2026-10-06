from pathlib import Path
import time
import pythoncom
import win32com.client as w

pythoncom.CoInitialize()
s=w.DispatchEx('SldWorks.Application')
for attempt in range(3):
    try:
        s.Visible=True
        print('visible',s.Visible,flush=True)
        break
    except Exception as exc:
        print('visible attempt',attempt+1,repr(exc),flush=True)
        time.sleep(2)
status=s.LoadAddIn(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
print('Flow load status',status,flush=True)
model=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
e=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
warn=w.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
d=s.OpenDoc6(str(model),2,0,'',e,warn)
print('Model open',bool(d),'error',e.value,'warning',warn.value,flush=True)
print('Flow object after model',bool(s.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')),flush=True)
print('Visible at end',s.Visible,flush=True)
