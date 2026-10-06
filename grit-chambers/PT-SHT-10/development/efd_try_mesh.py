exec(open(r'work\efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
s=typed(p.GetSolver(),'IProjectSolver')
try:
 print('create mesh start',flush=True)
 x=s.CreateMesh(True,False)
 print('create mesh result',x,flush=True)
except Exception as e:print('mesh error',repr(e),flush=True)
try:print('rebuild error',p.GetLastRebuildError(),flush=True)
except Exception as e:print('rebuild error fetch',repr(e),flush=True)
