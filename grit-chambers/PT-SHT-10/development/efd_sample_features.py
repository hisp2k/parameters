exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
print('title',doc.GetTitle(),'project',p.GetName())
f=typed(p.GetFeatures(),'IProjectFeatures')
for method,args in [('GetFeatures1',(True,)),('GetFeatures2',(True,0)),('GetFeatures2',(True,62))]:
 try:
  x=getattr(f,method)(*args)
  print(method,args,'type',type(x),'len',len(x) if x else 0)
  if x:
   for v in x:
    print('  ',v.GetName(),v.GetType(),v.GetUUID())
 except Exception as e:print(method,'ERR',repr(e))
