import os
import sys
import traceback
from pathlib import Path

import pythoncom
import win32com.client

pythoncom.CoInitialize()
sw = win32com.client.DispatchEx('SldWorks.Application')
sw.Visible = True
print('SOLIDWORKS revision:', sw.RevisionNumber, flush=True)
def open_model():
    model = next((Path.cwd() / 'work' / 'pt-sht-10-working-copy' / 'Модель').glob('*Бункер в сборе.SLDASM'))
    errors = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32com.client.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    doc = sw.OpenDoc6(str(model), 2, 64, '', errors, warnings)
    print('Model open:', bool(doc), 'errors:', errors.value, 'warnings:', warnings.value, flush=True)

if '--load-first' not in sys.argv and '--blank' not in sys.argv:
    open_model()
elif '--blank' in sys.argv:
    print('Blank SOLIDWORKS instance; no model opened', flush=True)
addin_path = r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll'
try:
    result = sw.LoadAddIn(addin_path)
    print('LoadAddIn result:', result, flush=True)
    addin = sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')
    print('Flow add-in object:', bool(addin), flush=True)
    if result == 0 and '--load-first' in sys.argv:
        open_model()
        print('Flow add-in object after model open:', bool(sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')), flush=True)
except Exception as exc:
    print('LoadAddIn exception:', repr(exc), flush=True)
    traceback.print_exc()
finally:
    try:
        sw.ExitApp()
        print('Isolated SOLIDWORKS instance closed', flush=True)
    except Exception as exc:
        print('Isolated SOLIDWORKS could not close through COM:', repr(exc), flush=True)
