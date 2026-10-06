import pythoncom
import win32com.client as w
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
g=typed(p.GetGeneralSettings(),'IGeneralSettings')
print('before',g.GetComputationalDomain(0),flush=True)
bounds=(-0.38,-0.02,-0.38,0.38,0.9,0.40)
try:
    print('set',g.SetComputationalDomain(0,bounds,bounds),flush=True)
except Exception as e:
    print('set failed',repr(e),flush=True)
print('after',g.GetComputationalDomain(0),flush=True)
try:
    print('rebuild',p.Rebuild(True,True,True,False,False,False),flush=True)
    print('error',p.GetLastRebuildError(),flush=True)
except Exception as e:print('rebuild failed',repr(e),flush=True)
