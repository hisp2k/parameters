exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures')
for raw in f.GetFeatures2(True,0):
 b=typed(raw,'IBoundaryCondition')
 print('\nBC',b.GetName(),'fctype',b.get_FCType(),'uuid',b.GetUUID())
 for m in ['GetTopologicalReferencesUUIDsAndNames','GetTopologicalReferencesUUIDsAndNames_VAR']:
  for args in [(None,None),([],[])]:
   try:print(m,args,getattr(b,m)(*args))
   except Exception as e:print(m,args,'ERR',repr(e))
 for k in [0,3,18,19,20,21,22,23]:
  try:
   q=b.GetParameter(k)
   print('param',k,'obj',bool(q),'value',q.GetValue(0.0) if q else None)
  except Exception as e: print('param',k,'ERR',repr(e))
