from pathlib import Path
import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
sw=win32.DispatchEx('SldWorks.Application')
try:
    print('load',sw.LoadAddIn(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll'),flush=True)
    model=next((Path.cwd()/'work'/'pt-sht-10-working-copy'/'Модель').glob('*Бункер в сборе.SLDASM'))
    e=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    w=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    doc=sw.OpenDoc6(str(model),2,64,'',e,w)
    print('model',bool(doc),'err',e.value,'warn',w.value,flush=True)
    app=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')
    print('api type',app._oleobj_.GetTypeInfo().GetDocumentation(-1)[0],flush=True)
    api=app.GetAPI()
    print('api',bool(api),api._oleobj_.GetTypeInfo().GetDocumentation(-1)[0],flush=True)
    ti=api._oleobj_.GetTypeInfo()
    print('api methods',[ti.GetNames(ti.GetFuncDesc(i)[0]) for i in range(ti.GetTypeAttr()[6])],flush=True)
    edoc=api.IActiveDoc
    print('efd doc',bool(edoc),'type',edoc._oleobj_.GetTypeInfo().GetDocumentation(-1)[0],flush=True)
    ps=edoc.Projects
    print('projects value',ps,'type',type(ps),flush=True)
finally:
    sw.ExitApp()
