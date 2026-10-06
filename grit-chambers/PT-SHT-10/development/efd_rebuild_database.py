exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
for args in [(False,False,False,True,True,False),(True,True,False,True,True,False)]:
 try:print('rebuild',args,p.Rebuild(*args),'last',p.GetLastRebuildError(),flush=True)
 except Exception as e:print('ERR',repr(e),flush=True)
