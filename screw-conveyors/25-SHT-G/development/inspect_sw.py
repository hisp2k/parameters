import glob
import os
import win32com.client as win32
import pythoncom

base = r'C:\Users\adm\Desktop\25.SHT.G.00.00.00.00'
asm = glob.glob(os.path.join(base, '**', '*Транспортер.SLDASM'), recursive=True)[0]
print('ASM', asm, flush=True)
sw = win32.Dispatch('SldWorks.Application')
sw.Visible = False
print('SW', sw.RevisionNumber, flush=True)
try:
    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    model = sw.OpenDoc6(asm, 2, 1, '', errors, warnings)
    print('open status', errors.value, warnings.value, flush=True)
    print('MODEL', bool(model), type(model), flush=True)
    if model:
        print('title', model.GetTitle, flush=True)
        print('path', model.GetPathName, flush=True)
        eq = model.GetEquationMgr
        print('equations', eq.GetCount, flush=True)
        conf = model.GetActiveConfiguration
        root = conf.GetRootComponent3(True)
        comps = root.GetChildren
        print('rootchildren', len(comps), flush=True)
        for c in comps:
            print(c.Name2, c.GetPathName, c.IsSuppressed, flush=True)
except Exception as e:
    print('ERROR', repr(e), flush=True)
