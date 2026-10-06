from pathlib import Path
import pythoncom
import win32com.client as win32

sw = win32.GetActiveObject('SldWorks.Application')
doc = sw.ActiveDoc
mgr = doc.GetEquationMgr
old = mgr.Equation(0)
new = old.replace('36', '37')
print('old', old.encode('unicode_escape').decode())
for args in [(0, new), (new, 0)]:
    try:
        print('result', mgr._oleobj_.InvokeTypes(8, 0, pythoncom.DISPATCH_PROPERTYPUT,
              (pythoncom.VT_EMPTY, 0), ((pythoncom.VT_I4, 1), (pythoncom.VT_BSTR, 1)), *args))
        print('now', mgr.Equation(0).encode('unicode_escape').decode())
    except Exception as exc:
        print('error', repr(exc))
try:
    mgr._oleobj_.InvokeTypes(8, 0, pythoncom.DISPATCH_PROPERTYPUT,
          (pythoncom.VT_EMPTY, 0), ((pythoncom.VT_I4, 1), (pythoncom.VT_BSTR, 1)), 0, old)
    print('restored', mgr.Equation(0).encode('unicode_escape').decode())
except Exception as exc:
    print('restore error', repr(exc))
