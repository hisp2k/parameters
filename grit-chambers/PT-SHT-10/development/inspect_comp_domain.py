exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
g=typed(p.GetGeneralSettings(),'IGeneralSettings')
for k in range(0,12):
 try:print(k,g.GetComputationalDomain(k))
 except Exception as e:print(k,'ERR',repr(e))
