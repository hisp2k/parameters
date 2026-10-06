import sys
sys.stdout.reconfigure(encoding='utf-8')
exec(open('work/efd_project_inspect.py',encoding='utf-8').read().split("print('project'")[0])
assert p.GetName()=='PT-SHT-10-210L-Q10-closed'
app.SetSilent()
try:
    print('REBUILD',p.Rebuild(False,True,True,False,False,False),repr(p.GetLastRebuildError()),flush=True)
    f=typed(p.GetFeatures(),'IProjectFeatures')
    for raw in f.GetFeatures2(True,0) or []:
        b=typed(raw,'IBoundaryCondition')
        print('BC',b.GetName(),b.get_FCType(),b.GetTopologicalReferencesUUIDsAndNames(None,None),
              'P3',b.GetParameter(3).GetValue(0.),'P18',b.GetParameter(18).GetValue(0.),flush=True)
finally:
    app.ResetSilent()
