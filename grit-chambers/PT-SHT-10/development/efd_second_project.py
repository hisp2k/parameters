exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
print('old',p.GetName(),flush=True)
new=doc.CreateProject(None)
print('created',bool(new),flush=True)
if new:
 q=typed(new,'IProject');q.SetName('PT-SHT-10-demo-Q10-sealed');print('name',q.GetName(),flush=True)
 try:print('add',doc.AddProject(q,'По умолчанию'),flush=True)
 except Exception as e:print('add ERR',repr(e),flush=True)
 print('active',typed(doc.GetActiveProject(),'IProject').GetName(),flush=True)
