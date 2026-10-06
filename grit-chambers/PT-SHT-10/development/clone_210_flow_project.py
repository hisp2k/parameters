import sys
sys.stdout.reconfigure(encoding='utf-8')
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
projects=[]
for raw in doc.GetProjects1() or []:
    candidate=typed(raw,'IProject')
    projects.append(candidate)
    print('PROJECT',candidate.GetName(),flush=True)
old=next(x for x in projects if x.GetName()=='PT-SHT-10-demo-Q10-sealed')
assert not any(x.GetName()=='PT-SHT-10-210L-cloned' for x in projects)
app.SetSilent()
try:
    new=typed(doc.CreateProject(old),'IProject')
    print('CREATE',new.GetName(),flush=True)
    new.SetName('PT-SHT-10-210L-cloned')
    print('ADD',doc.AddProject(new,'По умолчанию'),flush=True)
    print('ACTIVE',typed(doc.GetActiveProject(),'IProject').GetName(),flush=True)
    f=typed(new.GetFeatures(),'IProjectFeatures')
    print('BC_COUNT',len(f.GetFeatures2(True,0) or []),flush=True)
    print('REBUILD',new.Rebuild(False,False,True,False,False,False),repr(new.GetLastRebuildError()),flush=True)
finally:
    app.ResetSilent()
