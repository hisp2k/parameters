exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
print('active',p.GetName())
f=typed(p.GetFeatures(),'IProjectFeatures')
for o in f.GetFeatures2(True,0) or []:
 print('FEATURE',o.GetName(),o.GetUUID())
 try:
  b=typed(o,'IBoundaryCondition')
  print('FC',b.get_FCType(),'P18',b.GetParameter(18).GetValue())
 except Exception as e:print('ERR',str(e)[:200])
