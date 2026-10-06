exec(open(r'work\efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures')
try:
 bc=f.CreateFeature(0)
 print('created',bc)
 if bc:
  b=typed(bc,'IBoundaryCondition');print('name',b.GetName(),'type',b.GetType(),'params',b.GetParameters())
except Exception as e: print('ERROR',repr(e))
