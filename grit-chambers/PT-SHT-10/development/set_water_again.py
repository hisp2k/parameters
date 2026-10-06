exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
sub=typed(p.GetProjectSubstances(),'IProjectSubstances');water='6D4EB34F944911D4B47100A024552746'
print('add',sub.AddSubstance(2,water),'default',sub.SetDefaultFluid(water,True))
print('rebuild',p.Rebuild(True,True,True,False,False,False));print('last',p.GetLastRebuildError())
