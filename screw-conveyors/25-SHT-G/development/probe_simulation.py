from pathlib import Path
import pythoncom
import win32com.client as w

root = Path('work/simulation_test/25.SHT.G_parameterized').resolve()
part = list(root.glob('*02.00.00.02*Вал*SLDPRT'))[0]
sw = w.Dispatch('SldWorks.Application')
e = w.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
warn = w.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
m = sw.OpenDoc6(str(part), 1, 1, '', e, warn)
print('open', bool(m), e.value)
sw.ActivateDoc2(m.GetTitle, False, e)
add = sw.GetAddInObject('SldWorks.Simulation')
if not add:
    print('load', sw.LoadAddIn(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\Simulation\cosworks.dll'))
    add = sw.GetAddInObject('SldWorks.Simulation')
print('addin', bool(add))
cw = add.COSMOSWORKS
doc = cw.ActiveDoc
print('cwd', bool(doc))
sm = doc.StudyManager
print('study count', sm.StudyCount)
err = w.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
study = sm.CreateNewStudy3('PROBE_STATIC', 0, 0, err)
print('study', bool(study), err.value)
solid = study.SolidManager
for i in (0, 1):
    err.value = 0
    try:
        comp = solid.GetComponentAt(i, err)
        print('component', i, bool(comp), err.value)
        if comp:
            for j in (0, 1):
                try:
                    body = comp.GetSolidBodyAt(j, err)
                    print(' body', j, bool(body), err.value)
                except Exception as ex:
                    print(' body error', j, str(ex)[:200])
    except Exception as ex:
        print('component error', i, str(ex)[:200])
m.Save3(1, e, warn)
print('saved', e.value, warn.value)
sw.CloseDoc(m.GetTitle)
