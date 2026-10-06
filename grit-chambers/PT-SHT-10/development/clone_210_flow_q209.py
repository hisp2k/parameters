import sys
sys.stdout.reconfigure(encoding='utf-8')
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
assert p.GetName()=='PT-SHT-10-210L-cloned'
assert not any(typed(x,'IProject').GetName()=='PT-SHT-10-210L-Q2p09' for x in doc.GetProjects1() or [])
app.SetSilent()
try:
    q=typed(doc.CreateProject(p),'IProject')
    q.SetName('PT-SHT-10-210L-Q2p09')
    assert doc.AddProject(q,'По умолчанию')
    f=typed(q.GetFeatures(),'IProjectFeatures')
    inlet=next(x for x in f.GetFeatures2(True,0) if x.GetName()=='Inlet')
    bc=typed(inlet,'IBoundaryCondition')
    assert bc.get_FCType()==1
    assert bc.GetParameter(18).SetValue(2.09/3600)
    print('INLET',bc.GetParameter(18).GetValue(),flush=True)
    assert q.Rebuild(False,False,True,False,False,False),q.GetLastRebuildError()
    print('PROJECT',q.GetName(),flush=True)
    print('SOLVE START',flush=True)
    solver=typed(q.GetSolver(),'IProjectSolver')
    print('SOLVE RESULT',solver.Solve(False,True,True,False),q.GetLastRebuildError(),flush=True)
finally:
    app.ResetSilent()
