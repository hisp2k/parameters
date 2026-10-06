from pathlib import Path
import pythoncom
import win32com.client as win32

pythoncom.CoInitialize()
sw=win32.DispatchEx('SldWorks.Application')
try:
    status=sw.LoadAddIn(r'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS Flow Simulation\binCFW\FW03.dll')
    print('Flow load status',status,flush=True)
    model=next((Path.cwd()/'work'/'pt-sht-10-demo'/'Модель').glob('*Бункер в сборе.SLDASM'))
    e=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    w=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
    doc=sw.OpenDoc6(str(model),2,64,'',e,w)
    print('Model open',bool(doc),'error',e.value,'warning',w.value,flush=True)
    app=sw.GetAddInObject('{85914DF7-BA25-4A2A-808A-769E28ADDA94}')
    api=app.GetAPI()
    edoc=api.IActiveDoc
    print('Existing projects',edoc.Projects,flush=True)
    p=edoc.CreateTemplateProject(None)
    print('Created project',bool(p),p._oleobj_.GetTypeInfo().GetDocumentation(-1)[0] if p else None,flush=True)
    print('Projects after',edoc.Projects,flush=True)
    if p:
        try:
            p.ProjectName='PT-SHT-10-demo-Q10'
            print('Name',p.ProjectName,flush=True)
        except Exception as exc:
            print('Project name error',repr(exc),flush=True)
        try:
            added=edoc.AddProject2(p,'PT-SHT-10-demo-Q10','По умолчанию',True,True)
            print('AddProject2',added,'projects',edoc.Projects,flush=True)
        except Exception as exc:
            print('AddProject2 error',repr(exc),flush=True)
        se=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
        swarn=win32.VARIANT(pythoncom.VT_BYREF|pythoncom.VT_I4,0)
        print('Save3',doc.Save3(1,se,swarn),'error',se.value,'warning',swarn.value,flush=True)
finally:
    sw.ExitApp()
