exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
f=typed(p.GetFeatures(),'IProjectFeatures')
for b in f.GetFeatures2(True,0) or []:
 print('remove',b.GetName(),flush=True)
 try:print('result',f.RemoveFeature(b.GetUUID()),flush=True)
 except Exception as e:print('ERR',repr(e),flush=True)
print('now',f.GetFeatures2(True,0),flush=True)
